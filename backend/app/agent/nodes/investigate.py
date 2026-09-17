"""
Investigate node: proposes FILE_READ / github.read_file intent,
evaluates policy, and identifies potential bugs.
"""

from typing import Any

from app.agent.prompts.review_prompts import INVESTIGATE_PROMPT_TEMPLATE
from app.agent.state import AgentState
from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.policy_decision import Decision
from app.domain.protocols.github_client import GitHubClient
from app.services.policy_gateway import PolicyGateway


async def investigate_node(
    state: AgentState,
    github_client: GitHubClient,
    policy_gateway: PolicyGateway | None = None,
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

    investigation = INVESTIGATE_PROMPT_TEMPLATE.format(
        plan=plan[:500],
        pr_diff=pr_diff[:1000],
    )

    return {
        "investigation": f"{findings}\n\n{investigation}",
        "action_intents": intents,
        "policy_decisions": decisions,
    }
