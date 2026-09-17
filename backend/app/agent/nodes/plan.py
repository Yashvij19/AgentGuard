"""
Plan node: proposes FILE_READ / github.read_pr intent, evaluates policy,
and drafts an analysis plan.
"""

from typing import Any

from app.agent.prompts.review_prompts import PLAN_PROMPT_TEMPLATE
from app.agent.state import AgentState
from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.policy_decision import Decision
from app.domain.protocols.github_client import GitHubClient
from app.services.policy_gateway import PolicyGateway


async def plan_node(
    state: AgentState,
    github_client: GitHubClient,
    policy_gateway: PolicyGateway | None = None,
) -> dict[str, Any]:
    """
    Evaluate policy permission to read PR diff, then formulate a structured review plan.
    """
    repo = state["repo"]
    pr_number = state["pr_number"]
    run_id = state["run_id"]

    intents = list(state.get("action_intents", []))
    decisions = list(state.get("policy_decisions", []))

    # 1. Construct ActionIntent for reading the PR
    intent = ActionIntent(
        run_id=run_id,
        action=ActionType.FILE_READ,
        target=f"pull_requests/{pr_number}/diff",
        operation="read",
        capability="github.read_pr",
        reason="Read PR diff and file metadata to formulate security analysis plan",
    )
    intents.append(intent.model_dump(mode="json"))

    # 2. Evaluate Policy Gateway if present
    if policy_gateway:
        verdict = await policy_gateway.evaluate_intent(intent, repo)
        decisions.append(verdict.model_dump(mode="json"))

        if verdict.decision != Decision.ALLOW:
            return {
                "action_intents": intents,
                "policy_decisions": decisions,
                "halted": True,
                "halt_reason": f"Plan step halted: {verdict.reason} (verdict: {verdict.decision.value})",
            }

    # 3. Fetch Diff & Changed Files from GitHub
    pr_diff = await github_client.get_pr_diff(repo, pr_number)
    changed_files = await github_client.get_pr_files(repo, pr_number)

    # 4. Synthesize Plan
    diff_preview = pr_diff[:1500] + ("\n... [truncated]" if len(pr_diff) > 1500 else "")
    file_list_str = "\n".join(f"- {f}" for f in changed_files[:20])

    plan_summary = PLAN_PROMPT_TEMPLATE.format(
        repo=repo,
        pr_number=pr_number,
        file_count=len(changed_files),
        file_list=file_list_str,
        diff_preview=diff_preview,
    )

    return {
        "pr_diff": pr_diff,
        "changed_files": changed_files,
        "plan": plan_summary,
        "action_intents": intents,
        "policy_decisions": decisions,
    }
