"""
Domain model representing an incoming GitHub webhook delivery for idempotency.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WebhookDelivery(BaseModel):
    """Records an incoming webhook delivery to prevent duplicate processing."""

    id: UUID = Field(default_factory=uuid4)
    github_delivery_id: str = Field(
        ..., description="Unique delivery GUID from X-GitHub-Delivery header"
    )
    event_type: str = Field(..., description="GitHub event name (e.g. pull_request)")
    payload_summary: dict[str, Any] = Field(
        default_factory=dict, description="Sanitized summary of payload for audit"
    )
    run_id: UUID | None = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
