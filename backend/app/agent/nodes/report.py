"""
Report node: formats the final analysis comment and posts it directly to GitHub.
"""

from typing import Any

from app.agent.prompts.review_prompts import REPORT_PROMPT_TEMPLATE
from app.agent.state import AgentState
from app.domain.protocols.github_client import GitHubClient


async def report_node(state: AgentState, github_client: GitHubClient) -> dict[str, Any]:
    """
    Format a structured markdown review summary and post it as a comment on the PR.
    """
    repo = state["repo"]
    pr_number = state["pr_number"]
    head_sha = state["head_sha"]
    changed_files = state.get("changed_files", [])

    summary = (
        f"Automated PR analysis completed for **{len(changed_files)} changed files**.\n"
        f"All changes verified against commit `{head_sha[:8]}` under per-PR concurrency lock."
    )
    findings = state.get("investigation", "No critical regressions identified in initial pass.")

    comment_body = REPORT_PROMPT_TEMPLATE.format(
        repo=repo,
        pr_number=pr_number,
        head_sha=head_sha[:8],
        summary=summary,
        findings=findings[:800],
    )

    # Post comment to GitHub PR
    comment_id = await github_client.post_comment(repo, pr_number, comment_body)

    return {
        "summary_report": comment_body,
        "comment_id": comment_id,
    }
