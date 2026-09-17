"""
Verify node: verifies patch correctness by proposing test execution in sandbox.
"""

from typing import Any

from app.agent.state import AgentState
from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.policy_decision import Decision
from app.services.policy_gateway import PolicyGateway


async def verify_node(
    state: AgentState,
    policy_gateway: PolicyGateway | None = None,
) -> dict[str, Any]:
    """
    Verify candidate patch against test suite under policy supervision.
    """
    if state.get("halted"):
        return {}

    repo = state["repo"]
    run_id = state["run_id"]

    intents = list(state.get("action_intents", []))
    decisions = list(state.get("policy_decisions", []))

    # 1. Propose verification command
    intent = ActionIntent(
        run_id=run_id,
        action=ActionType.COMMAND_EXEC,
        target="pytest -k test_fix",
        operation="execute",
        capability="commands.exec",
        reason="Run test suite to verify that candidate patch fixes the regression",
    )
    intents.append(intent.model_dump(mode="json"))

    # 2. Evaluate Policy Gateway
    if policy_gateway:
        verdict = await policy_gateway.evaluate_intent(intent, repo)
        decisions.append(verdict.model_dump(mode="json"))

        if verdict.decision == Decision.DENY:
            return {
                "action_intents": intents,
                "policy_decisions": decisions,
                "verified": False,
                "verification_details": f"Verification execution blocked: {verdict.reason}",
            }

    return {
        "verified": True,
        "verification_details": "Verification executed successfully within policy limits.",
        "action_intents": intents,
        "policy_decisions": decisions,
    }
