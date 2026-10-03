"""
Pydantic schemas for the System Logs API.
Standardized developer JSON structure for logs, filtering, and manual creation.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SystemLogItem(BaseModel):
    """Schema representing an individual structured developer system log."""

    id: UUID
    timestamp: datetime
    level: str
    source: str
    api_name: str | None = None
    message: str
    task_progress: str | None = None
    status: str
    commit_sha: str | None = None
    pr_number: int | None = None
    repo: str | None = None
    run_id: UUID | None = None
    latency_ms: int = 0
    extra_info: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime


class PaginatedLogsResponse(BaseModel):
    """Paginated collection of developer system logs."""

    items: list[SystemLogItem]
    total: int
    limit: int
    offset: int


class CreateLogRequest(BaseModel):
    """Payload to create a custom developer log entry."""

    level: str = "INFO"
    source: str = "developer"
    api_name: str | None = None
    message: str
    task_progress: str | None = None
    commit_sha: str | None = None
    pr_number: int | None = None
    repo: str | None = None
    run_id: UUID | None = None
    status: str = "PASS"
    latency_ms: int = 0
    extra_info: dict[str, Any] = Field(default_factory=dict)
