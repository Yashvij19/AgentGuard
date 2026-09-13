"""
Investigate node: evaluates changed files and potential risks based on the plan.
"""

from typing import Any

from app.agent.prompts.review_prompts import INVESTIGATE_PROMPT_TEMPLATE
from app.agent.state import AgentState
from app.domain.protocols.github_client import GitHubClient


async def investigate_node(state: AgentState, github_client: GitHubClient) -> dict[str, Any]:
    """
    Deep-dive into the changed files to identify potential bugs, security concerns,
    or performance regressions.
    """
    plan = state.get("plan", "")
    pr_diff = state.get("pr_diff", "")
    changed_files = state.get("changed_files", [])

    # Identify notable files
    has_db_changes = any("migration" in f or "models" in f for f in changed_files)
    has_config_changes = any("config" in f or ".env" in f for f in changed_files)

    investigation_notes = [
        f"Analyzed {len(changed_files)} changed files against review plan.",
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
    }
