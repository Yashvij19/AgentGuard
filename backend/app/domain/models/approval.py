"""
Domain models for the Human-in-the-Loop (HITL) approval system.
Defines lifecycle statuses, approval queue entries, and decision results.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.domain.models.action_intent import ActionIntent
from app.domain.models.policy_decision import PolicyDecision


class ApprovalStatus(StrEnum):
    """Lifecycle status of a human approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Approval(BaseModel):
    """
    Represents an action paused in the queue awaiting human review.
    Connects the proposed ActionIntent with the policy verdict and reviewer decision.
    """

    id: UUID = Field(default_factory=uuid4)
    run_id: UUID = Field(..., description="ID of the associated run")
    event_id: UUID | None = Field(
        default=None,
        description="ID of the RunEvent that recorded this approval request",
    )
    status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING,
        description="Current state in the approval lifecycle",
    )
    action_intent: dict[str, Any] = Field(
        ...,
        description="Serialized ActionIntent that triggered the approval requirement",
    )
    decision_trace: dict[str, Any] = Field(
        default_factory=dict,
        description="Evaluation trace from PolicyGateway including risk and OPA match",
    )
    requested_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when approval was requested",
    )
    decided_at: datetime | None = Field(
        default=None,
        description="Timestamp when reviewer made the decision or approval expired",
    )
    decided_by: str | None = Field(
        default=None,
        description="Identifier of the human reviewer who made the decision",
    )
    rejection_reason: str | None = Field(
        default=None,
        description="Rationale provided by reviewer if the action was rejected",
    )

    def approve(self, decided_by: str) -> None:
        """Mark approval as granted by a reviewer."""
        self.status = ApprovalStatus.APPROVED
        self.decided_by = decided_by
        self.decided_at = datetime.now(UTC)

    def reject(self, decided_by: str, reason: str | None = None) -> None:
        """Mark approval as rejected by a reviewer."""
        self.status = ApprovalStatus.REJECTED
        self.decided_by = decided_by
        self.rejection_reason = reason
        self.decided_at = datetime.now(UTC)

    def expire(self) -> None:
        """Mark approval as expired due to exceeding pending timeout."""
        self.status = ApprovalStatus.EXPIRED
        self.decided_at = datetime.now(UTC)


class ApprovalRequest(BaseModel):
    """Payload for submitting an ActionIntent to the approval queue."""

    run_id: UUID
    action_intent: ActionIntent
    decision: PolicyDecision


class ApprovalDecisionResult(BaseModel):
    """Result of an operator approving or rejecting an approval request."""

    approval_id: UUID
    run_id: UUID
    status: ApprovalStatus
    decided_by: str
    action_executed: bool = False
    execution_result: dict[str, Any] | None = None
    message: str = ""
