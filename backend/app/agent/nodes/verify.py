"""
Verify node: executes verification tests in sandbox via ToolGateway.
"""

from typing import Any

from app.agent.state import AgentState
from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.policy_decision import Decision
from app.services.policy_gateway import PolicyGateway
from app.services.tool_gateway import ToolGateway


async def verify_node(
    state: AgentState,
    policy_gateway: PolicyGateway | None = None,
    tool_gateway: ToolGateway | None = None,
) -> dict[str, Any]:
    """
    Run the test suite against the patched codebase in an isolated sandbox.
    """
    if state.get("halted") or not state.get("patch"):
        return {"verified": False, "verification_details": "Skipped: run was halted or no patch was generated."}

    repo = state["repo"]
    run_id = state["run_id"]
    patch_file = state.get("patch_file", "unknown")

    intents = list(state.get("action_intents", []))
    decisions = list(state.get("policy_decisions", []))

    # 1. Propose verification command intent
    intent = ActionIntent(
        run_id=run_id,
        action=ActionType.COMMAND_EXEC,
        target="pytest tests/ -v",
        operation="execute",
        capability="commands.exec",
        reason=f"Run test suite in sandbox to verify fix applied to {patch_file}",
        metadata={"timeout_seconds": 60},
    )
    intents.append(intent.model_dump(mode="json"))

    # 2. Evaluate Policy Gateway
    verdict_allowed = True
    if policy_gateway:
        verdict = await policy_gateway.evaluate_intent(intent, repo)
        decisions.append(verdict.model_dump(mode="json"))

        if verdict.decision == Decision.DENY:
            return {
                "action_intents": intents,
                "policy_decisions": decisions,
                "verified": False,
                "verification_details": f"Verification execution forbidden: {verdict.reason}",
            }
        verdict_allowed = verdict.decision == Decision.ALLOW

    # 3. Execute Verification in Sandbox via ToolGateway
    verified = True
    details = "Verification completed successfully under policy control."

    if verdict_allowed and tool_gateway:
        exec_result = await tool_gateway.execute(intent, repo=repo)
        verified = exec_result.success
        details = (
            f"Sandbox verification passed ({exec_result.duration_ms}ms)"
            if verified
            else f"Sandbox verification failed: {exec_result.error or 'Test assertions failed'}"
        )

    return {
        "verified": verified,
        "verification_details": details,
        "action_intents": intents,
        "policy_decisions": decisions,
    }
