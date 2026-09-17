"""
Policy Decision domain models.
Captures verdicts produced by OPA, Risk, and Budget evaluation.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Decision(StrEnum):
    """Tri-state policy evaluation verdict."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class PolicyDecision(BaseModel):
    """
    Immutable audit record of a policy decision made for a specific ActionIntent.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique decision identifier",
    )
    run_id: UUID = Field(
        description="Associated run ID",
    )
    action_intent_id: UUID = Field(
        description="UUID of the ActionIntent that was evaluated",
    )
    decision: Decision = Field(
        description="Evaluation verdict: ALLOW, DENY, or REQUIRE_APPROVAL",
    )
    rule_matched: str | None = Field(
        default=None,
        description="Identifier of the specific policy rule that determined this verdict",
    )
    risk_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Calculated risk score from 0 to 100",
    )
    policy_version: int = Field(
        default=1,
        ge=1,
        description="Monotonically increasing version of the policy evaluated",
    )
    opa_query_id: str | None = Field(
        default=None,
        description="Correlation ID from the OPA decision log",
    )
    reason: str = Field(
        default="",
        description="Human-readable explanation of the verdict",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Auxiliary diagnostic data from policy evaluation",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the decision was finalized",
    )
