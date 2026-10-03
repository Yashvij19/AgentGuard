"""
Patch node: synthesizes code fix via LLMGateway and emits FILE_WRITE / github.create_commit ActionIntent.
"""

from typing import Any

from app.agent.state import AgentState
from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.llm_config import TaskType
from app.domain.models.policy_decision import Decision
from app.services.approval_service import ApprovalService
from app.services.llm_gateway import LLMGateway
from app.services.policy_gateway import PolicyGateway
from app.services.tool_gateway import ToolGateway


async def patch_node(
    state: AgentState,
    policy_gateway: PolicyGateway | None = None,
    tool_gateway: ToolGateway | None = None,
    llm_gateway: LLMGateway | None = None,
    approval_service: ApprovalService | None = None,
) -> dict[str, Any]:
    """
    Synthesize a candidate fix diff and evaluate whether policy permits applying it.
    """
    if state.get("halted"):
        return {}

    repo = state["repo"]
    run_id = state["run_id"]
    changed_files = state.get("changed_files", [])
    investigation = state.get("investigation", "")

    target_file = changed_files[0] if changed_files else "src/main.py"

    intents = list(state.get("action_intents", []))
    decisions = list(state.get("policy_decisions", []))

    # 1. Synthesize candidate diff using LLMGateway (or fallback)
    patch_diff: str
    if llm_gateway:
        try:
            prompt = (
                f"Repository: {repo}\nFile: {target_file}\n"
                f"Investigation Findings:\n{investigation[:500]}\n\n"
                "Synthesize a minimal unified git diff to resolve this issue."
            )
            llm_resp = await llm_gateway.generate(
                prompt=prompt,
                task_type=TaskType.CODE_GENERATION,
                run_id=run_id,
            )
            patch_diff = llm_resp.content.strip()
            if patch_diff.startswith("```diff"):
                patch_diff = patch_diff[len("```diff"):].strip()
            if patch_diff.startswith("```"):
                patch_diff = patch_diff[len("```"):].strip()
            if patch_diff.endswith("```"):
                patch_diff = patch_diff[:-3].strip()
            patch_tokens = llm_resp.total_tokens
            patch_cost = float(llm_resp.estimated_cost_usd)

        except Exception:
            patch_diff = f"--- a/{target_file}\n+++ b/{target_file}\n@@ -1,3 +1,4 @@\n+# Automated patch applied by AgentGuard\n"
            patch_tokens = 0
            patch_cost = 0.0
    else:
        patch_diff = f"--- a/{target_file}\n+++ b/{target_file}\n@@ -1,3 +1,4 @@\n+# Automated patch applied by AgentGuard\n"
        patch_tokens = 0
        patch_cost = 0.0


    # 2. Propose FILE_WRITE intent
    intent = ActionIntent(
        run_id=run_id,
        action=ActionType.FILE_WRITE,
        target=target_file,
        operation="modify",
        capability="github.create_commit",
        reason=f"Apply candidate patch to resolve regression in {target_file}",
        metadata={
            "diff": patch_diff,
            "diff_unified": patch_diff,
            "target_path": target_file,
            "repository": repo,
            "pr_number": state.get("pr_number"),
        },
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
            pending_id: str | None = None
            if approval_service:
                approval = await approval_service.request_approval(
                    run_id=run_id,
                    action_intent=intent,
                    decision=verdict,
                )
                pending_id = str(approval.id)
            return {
                "action_intents": intents,
                "policy_decisions": decisions,
                "patch": patch_diff,
                "patch_file": target_file,
                "paused": True,
                "pending_approval_id": pending_id,
                "pause_reason": f"Code modification on {target_file} requires human approval: {verdict.reason}",
                "halted": True,
                "halt_reason": f"Code modification on {target_file} requires human approval: {verdict.reason}",
                "total_tokens": int(state.get("total_tokens", 0)) + patch_tokens,
                "total_cost": float(state.get("total_cost", 0.0)) + patch_cost,
            }

    # 4. Stage patch via ToolGateway
    if tool_gateway:
        await tool_gateway.execute(intent, repo=repo)

    return {
        "patch": patch_diff,
        "patch_file": target_file,
        "action_intents": intents,
        "policy_decisions": decisions,
        "total_tokens": int(state.get("total_tokens", 0)) + patch_tokens,
        "total_cost": float(state.get("total_cost", 0.0)) + patch_cost,
    }


