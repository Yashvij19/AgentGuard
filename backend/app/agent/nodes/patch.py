"""
Patch node: synthesizes code fix and emits FILE_WRITE / github.create_commit ActionIntent.
"""

from typing import Any

from app.agent.state import AgentState
from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.policy_decision import Decision
from app.services.policy_gateway import PolicyGateway


async def patch_node(
    state: AgentState,
    policy_gateway: PolicyGateway | None = None,
) -> dict[str, Any]:
    """
    Synthesize a candidate fix diff and evaluate whether policy permits applying it.
    """
    if state.get("halted"):
        return {}

    repo = state["repo"]
    run_id = state["run_id"]
    changed_files = state.get("changed_files", [])

    # Pick candidate target file or fallback to standard application file
    target_file = changed_files[0] if changed_files else "src/main.py"

    intents = list(state.get("action_intents", []))
    decisions = list(state.get("policy_decisions", []))

    # 1. Synthesize candidate diff
    patch_diff = f"--- a/{target_file}\n+++ b/{target_file}\n@@ -1,3 +1,4 @@\n+# Automated patch applied by AgentGuard\n"

    # 2. Propose FILE_WRITE intent
    intent = ActionIntent(
        run_id=run_id,
        action=ActionType.FILE_WRITE,
        target=target_file,
        operation="modify",
        capability="github.create_commit",
        reason=f"Apply candidate patch to resolve regression in {target_file}",
        metadata={"diff": patch_diff},
    )
    intents.append(intent.model_dump(mode="json"))

    # 3. Evaluate Policy Gateway
    if policy_gateway:
        verdict = await policy_gateway.evaluate_intent(intent, repo)
        decisions.append(verdict.model_dump(mode="json"))

        if verdict.decision == Decision.DENY:
            return {
                "action_intents": intents,
                "policy_decisions": decisions,
                "patch": None,
                "patch_file": target_file,
                "halted": True,
                "halt_reason": f"Code modification denied on {target_file}: {verdict.reason}",
            }
        if verdict.decision == Decision.REQUIRE_APPROVAL:
            return {
                "action_intents": intents,
                "policy_decisions": decisions,
                "patch": patch_diff,
                "patch_file": target_file,
                "halted": True,
                "halt_reason": f"Code modification on {target_file} requires human approval: {verdict.reason}",
            }

    return {
        "patch": patch_diff,
        "patch_file": target_file,
        "action_intents": intents,
        "policy_decisions": decisions,
    }
