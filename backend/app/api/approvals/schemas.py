"""
Pydantic schemas for the Approvals REST API.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.models.approval import ApprovalStatus


class ApprovalResponse(BaseModel):
    """Detailed view of an approval request in the queue."""

    id: UUID
    run_id: UUID
    event_id: UUID | None = None
    status: ApprovalStatus
    action_intent: dict[str, Any]
    decision_trace: dict[str, Any]
    requested_at: datetime
    decided_at: datetime | None = None
    decided_by: str | None = None
    rejection_reason: str | None = None


class PaginatedApprovalsResponse(BaseModel):
    """Paginated collection of pending approvals."""

    items: list[ApprovalResponse]
    total: int
    limit: int
    offset: int


class ApproveActionRequest(BaseModel):
    """Payload for granting approval to a pending action."""

    decided_by: str = Field(
        ...,
        min_length=1,
        description="Username or email of the reviewer granting authorization",
        examples=["octocat@github.com"],
    )
    execute: bool = Field(
        default=True,
        description="Whether to immediately execute the approved action through ToolGateway",
    )


class RejectActionRequest(BaseModel):
    """Payload for rejecting a pending action."""

    decided_by: str = Field(
        ...,
        min_length=1,
        description="Username or email of the reviewer rejecting authorization",
        examples=["security_lead@company.com"],
    )
    reason: str | None = Field(
        default=None,
        description="Explanation for why the proposed action was declined",
        examples=["Cannot touch production credentials without change ticket"],
    )


class ApprovalDecisionResponse(BaseModel):
    """Response returned after processing an approval decision."""

    approval_id: UUID
    run_id: UUID
    status: ApprovalStatus
    decided_by: str
    action_executed: bool
    execution_result: dict[str, Any] | None = None
    message: str
