"""
Pydantic schemas for Policy Management API.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.models.policy import PolicyConfig


class PolicyResponse(BaseModel):
    """Response representing an active repository policy."""

    id: UUID
    repo: str
    yaml_content: str
    version: int
    parsed_content: PolicyConfig
    rego_bundle: str | None = None
    created_at: datetime
    updated_at: datetime


class PolicyUpdateRequest(BaseModel):
    """Payload for updating or creating a repository policy."""

    yaml_content: str = Field(
        min_length=1,
        description="Raw YAML policy string conforming to AgentGuard specification",
    )


class PolicyValidateRequest(BaseModel):
    """Payload for dry-run validating a YAML policy string."""

    yaml_content: str = Field(
        min_length=1,
        description="Raw YAML policy string to test without saving",
    )


class PolicyValidateResponse(BaseModel):
    """Result of a policy validation dry-run."""

    valid: bool
    version: int | None = None
    errors: list[str] = Field(default_factory=list)
    rego_data_preview: dict[str, Any] | None = None


class RegoBundleResponse(BaseModel):
    """Response containing compiled OPA data structure."""

    repo: str
    version: int
    rego_data: dict[str, Any]
