"""
State definition for the AgentGuard LangGraph workflow.
"""

from typing import Any, TypedDict
from uuid import UUID


class AgentState(TypedDict, total=False):
    """
    Centralized state dictionary passed between all LangGraph workflow nodes.
    total=False allows partial updates returned by individual nodes.
    """

    # Run Identifiers
    run_id: UUID
    repo: str
    pr_number: int
    head_sha: str

    # Context & Artifacts
    pr_diff: str
    changed_files: list[str]

    # Node Outputs
    plan: str
    investigation: str
    summary_report: str
    comment_id: int | None

    # Error Tracking
    error: str | None
    metadata: dict[str, Any]
