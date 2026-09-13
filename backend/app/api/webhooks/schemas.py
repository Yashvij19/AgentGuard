"""
Pydantic schemas for webhook API requests and responses.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class WebhookResponse(BaseModel):
    """Structured response returned after webhook ingestion."""

    status: str = Field(..., description="'accepted' when a run is initiated, 'ignored' otherwise")
    message: str = Field(..., description="Human-readable summary of the ingestion outcome")
    run_id: UUID | None = Field(default=None, description="UUID of the initiated Run, if applicable")
    delivery_id: str | None = Field(default=None, description="GitHub delivery GUID from X-GitHub-Delivery")
