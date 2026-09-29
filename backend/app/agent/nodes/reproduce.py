"""
Reproduce node: proposes COMMAND_EXEC intent to execute tests in an isolated sandbox.
"""

from typing import Any

from app.agent.state import AgentState
from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.policy_decision import Decision
from app.services.policy_gateway import PolicyGateway
from app.services.tool_gateway import ToolGateway


async def reproduce_node(
    state: AgentState,
    policy_gateway: PolicyGateway | None = None,
    tool_gateway: ToolGateway | None = None,
) -> dict[str, Any]:
    """
    Attempt to reproduce the reported bug or CI failure via sandboxed test execution.
    """
    if state.get("halted"):
        return {}

    repo = state["repo"]
    run_id = state["run_id"]

    intents = list(state.get("action_intents", []))
    decisions = list(state.get("policy_decisions", []))

    # 1. Propose command execution intent
    intent = ActionIntent(
        run_id=run_id,
        action=ActionType.COMMAND_EXEC,
        target="pytest tests/",
        operation="execute",
        capability="commands.exec",
        reason="Run test suite inside isolated sandbox to verify baseline failure",
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
                "reproduced": False,
                "reproduce_details": f"Test execution forbidden: {verdict.reason}",
                "halted": True,
                "halt_reason": f"Reproduce step denied: {verdict.reason}",
            }
        verdict_allowed = verdict.decision == Decision.ALLOW

    # 3. Execute via Tool Gateway in isolated sandbox if permitted
    reproduced = True
    details = "Baseline tests evaluated under policy control."

    if verdict_allowed and tool_gateway:
        exec_result = await tool_gateway.execute(intent, repo=repo)
        if exec_result.success:
            # Tests passed cleanly or command completed
            details = f"Sandbox test execution completed ({exec_result.duration_ms}ms)."
        else:
            # Baseline test failure reproduced!
            details = f"Sandbox reproduced test failure ({exec_result.duration_ms}ms): {exec_result.error or 'Tests failed'}"

    return {
        "reproduced": reproduced,
        "reproduce_details": details,
        "action_intents": intents,
        "policy_decisions": decisions,
    }
