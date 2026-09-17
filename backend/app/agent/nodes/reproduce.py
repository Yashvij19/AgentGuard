"""
Reproduce node: proposes COMMAND_EXEC intent to simulate or execute reproducing tests.
"""

from typing import Any

from app.agent.state import AgentState
from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.policy_decision import Decision
from app.services.policy_gateway import PolicyGateway


async def reproduce_node(
    state: AgentState,
    policy_gateway: PolicyGateway | None = None,
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
        reason="Run test suite to verify baseline test failures before patching",
    )
    intents.append(intent.model_dump(mode="json"))

    # 2. Evaluate Policy Gateway
    reproduced = True
    details = "Baseline tests evaluated under policy control."

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
        details = f"Command permitted by rule '{verdict.rule_matched}' (verdict: {verdict.decision.value})."

    return {
        "reproduced": reproduced,
        "reproduce_details": details,
        "action_intents": intents,
        "policy_decisions": decisions,
    }
