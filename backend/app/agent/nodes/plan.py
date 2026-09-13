"""
Plan node: analyzes PR metadata, diff, and changed files to draft an analysis plan.
"""

from typing import Any

from app.agent.prompts.review_prompts import PLAN_PROMPT_TEMPLATE
from app.agent.state import AgentState
from app.domain.protocols.github_client import GitHubClient


async def plan_node(state: AgentState, github_client: GitHubClient) -> dict[str, Any]:
    """
    Fetch PR diff and changed files, then formulate a structured review plan.
    """
    repo = state["repo"]
    pr_number = state["pr_number"]

    # 1. Fetch Diff & Changed Files from GitHub
    pr_diff = await github_client.get_pr_diff(repo, pr_number)
    changed_files = await github_client.get_pr_files(repo, pr_number)

    # 2. Synthesize Plan
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
    }
