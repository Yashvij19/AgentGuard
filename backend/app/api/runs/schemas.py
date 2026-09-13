"""
Pydantic schemas for the Runs API endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.models.run import RunStatus, TriggerType
from app.domain.models.run_event import EventType


class RunResponse(BaseModel):
    """Schema representing an individual AgentGuard run."""

    id: UUID
    repo: str
    pr_number: int
    head_sha: str
    trigger_type: TriggerType
    status: RunStatus
    policy_version: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_tokens: int = 0
    total_cost_usd: Decimal = Decimal("0.000000")
    created_at: datetime
    updated_at: datetime


class RunEventResponse(BaseModel):
    """Schema representing an audit event emitted during run execution."""

    id: UUID
    run_id: UUID
    step_name: str
    event_type: EventType
    content: dict[str, Any] = Field(default_factory=dict)
    tokens_used: int = 0
    latency_ms: int = 0
    created_at: datetime


class RunDetailResponse(BaseModel):
    """Detailed view of a run including its chronological event timeline."""

    run: RunResponse
    events: list[RunEventResponse] = Field(default_factory=list)


class PaginatedRunsResponse(BaseModel):
    """Paginated collection of runs."""

    items: list[RunResponse]
    total: int
    limit: int
    offset: int
