"""
Domain model representing an AgentGuard execution run.
"""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"  # Waiting for human approval
    STALE = "stale"  # Superseded by a newer commit
    COMPLETED = "completed"
    FAILED = "failed"


class TriggerType(StrEnum):
    PULL_REQUEST = "pull_request"
    CHECK_SUITE = "check_suite"


class Run(BaseModel):
    """Represents a single governed execution lifecycle for a PR or CI failure."""

    id: UUID = Field(default_factory=uuid4)
    repo: str = Field(..., description="Target repository in owner/repo format")
    pr_number: int = Field(..., description="Pull request number")
    head_sha: str = Field(..., description="Commit SHA bound to this run")
    trigger_type: TriggerType = Field(default=TriggerType.PULL_REQUEST)
    status: RunStatus = Field(default=RunStatus.QUEUED)
    policy_version: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_tokens: int = Field(default=0, ge=0)
    total_cost_usd: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def mark_running(self) -> None:
        self.status = RunStatus.RUNNING
        self.started_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def mark_paused(self) -> None:
        self.status = RunStatus.PAUSED
        self.updated_at = datetime.now(UTC)

    def mark_completed(self) -> None:
        self.status = RunStatus.COMPLETED
        self.completed_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def mark_failed(self) -> None:
        self.status = RunStatus.FAILED
        self.completed_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def mark_stale(self) -> None:
        self.status = RunStatus.STALE
        self.completed_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
