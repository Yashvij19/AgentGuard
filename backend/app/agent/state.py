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
    reproduced: bool | None
    reproduce_details: str | None
    patch: str | None
    patch_file: str | None
    verified: bool | None
    verification_details: str | None
    summary_report: str
    comment_id: int | None

    # Governance & Policy Tracking
    action_intents: list[dict[str, Any]]
    policy_decisions: list[dict[str, Any]]
    decision_traces: list[dict[str, Any]]
    halted: bool
    halt_reason: str | None
    paused: bool
    pending_approval_id: str | None
    pause_reason: str | None

    # Metrics & Accounting
    total_tokens: int
    total_cost: float

    # Error & Metadata Tracking
    error: str | None
    metadata: dict[str, Any]

