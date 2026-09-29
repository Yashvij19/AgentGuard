"""
Domain model representing an append-only event in an Agent run lifecycle.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(StrEnum):
    DECISION = "decision"
    ACTION_INTENT = "action_intent"
    TOOL_CALL = "tool_call"
    POLICY_DECISION = "policy_decision"
    LLM_CALL = "llm_call"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_EXPIRED = "approval_expired"



class RunEvent(BaseModel):
    """An immutable audit trail event logged during run execution."""

    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    step_name: str = Field(..., description="Workflow step e.g. plan, investigate, report")
    event_type: EventType
    content: dict[str, Any] = Field(default_factory=dict)
    tokens_used: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
