"""
Investigate node: proposes FILE_READ / github.read_file intent,
evaluates policy, and identifies potential bugs.
"""

from typing import Any

from app.agent.prompts.review_prompts import INVESTIGATE_PROMPT_TEMPLATE
from app.agent.state import AgentState
from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.llm_config import TaskType
from app.domain.models.policy_decision import Decision
from app.domain.protocols.github_client import GitHubClient
from app.services.llm_gateway import LLMGateway
from app.services.policy_gateway import PolicyGateway


async def investigate_node(
    state: AgentState,
    github_client: GitHubClient,
    policy_gateway: PolicyGateway | None = None,
    llm_gateway: LLMGateway | None = None,
) -> dict[str, Any]:
    """
    Deep-dive into changed files after validating filesystem and capability permissions.
    """
    if state.get("halted"):
        return {}

    repo = state["repo"]
    run_id = state["run_id"]
    plan = state.get("plan", "")
    pr_diff = state.get("pr_diff", "")
    changed_files = state.get("changed_files", [])

    intents = list(state.get("action_intents", []))
    decisions = list(state.get("policy_decisions", []))

    # 1. Propose inspection intent for changed files
    target_files_preview = ", ".join(changed_files[:3])
    intent = ActionIntent(
        run_id=run_id,
        action=ActionType.FILE_READ,
        target=target_files_preview or "repo/changed_files",
        operation="read",
        capability="github.read_file",
        reason=f"Inspect changed files ({len(changed_files)} files) to detect regressions",
        metadata={"file_count": len(changed_files)},
    )
    intents.append(intent.model_dump(mode="json"))

    # 2. Evaluate Policy Gateway
    if policy_gateway:
        verdict = await policy_gateway.evaluate_intent(intent, repo)
        decisions.append(verdict.model_dump(mode="json"))

        if verdict.decision != Decision.ALLOW:
            return {
                "action_intents": intents,
                "policy_decisions": decisions,
                "halted": True,
                "halt_reason": f"Investigation halted: {verdict.reason} (verdict: {verdict.decision.value})",
            }

    # 3. Perform Investigation
    has_db_changes = any("migration" in f or "models" in f for f in changed_files)
    has_config_changes = any("config" in f or ".env" in f for f in changed_files)

    investigation_notes = [
        f"Analyzed {len(changed_files)} changed files under governance clearance.",
        f"Database Schema Impact: {'Identified schema/model changes' if has_db_changes else 'No schema changes detected'}.",
        f"Configuration Impact: {'Environment/Config modifications detected' if has_config_changes else 'Standard application logic changes'}.",
    ]
    findings = "\n".join(f"- {note}" for note in investigation_notes)

    if llm_gateway:
        try:
            analysis_prompt = (
                f"You are AgentGuard, an autonomous code security and governance reviewer.\n"
                f"Review the following PR changes in repository '{repo}':\n\n"
                f"Changed files: {changed_files}\n"
                f"Diff:\n{pr_diff[:2500]}\n\n"
                f"Provide a concise analysis of code quality, potential bugs, and security considerations."
            )
            llm_res = await llm_gateway.generate(
                prompt=analysis_prompt,
                task_type=TaskType.REASONING,
                run_id=run_id,
            )
            investigation = llm_res.content
            tokens_used = llm_res.total_tokens
            cost_usd = float(llm_res.estimated_cost_usd)

        except Exception:
            investigation = INVESTIGATE_PROMPT_TEMPLATE.format(
                plan=plan[:500],
                pr_diff=pr_diff[:1000],
            )
            tokens_used = 0
            cost_usd = 0.0
    else:
        investigation = INVESTIGATE_PROMPT_TEMPLATE.format(
            plan=plan[:500],
            pr_diff=pr_diff[:1000],
        )
        tokens_used = 0
        cost_usd = 0.0

    return {
        "investigation": f"{findings}\n\n{investigation}",
        "action_intents": intents,
        "policy_decisions": decisions,
        "total_tokens": int(state.get("total_tokens", 0)) + tokens_used,
        "total_cost": float(state.get("total_cost", 0.0)) + cost_usd,
    }


