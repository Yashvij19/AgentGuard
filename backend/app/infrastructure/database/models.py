"""
SQLAlchemy 2.0 ORM models for AgentGuard.
Defines persistent schema for runs, webhook idempotency, and audit trails.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.approval import ApprovalStatus
from app.domain.models.run import RunStatus, TriggerType
from app.domain.models.run_event import EventType
from app.infrastructure.database.connection import Base


class WebhookDeliveryORM(Base):
    """
    Tracks GitHub webhook deliveries for strict idempotency enforcement.
    The unique constraint on github_delivery_id prevents double-processing.
    """

    __tablename__ = "webhook_deliveries"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    github_delivery_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        doc="GitHub delivery GUID from X-GitHub-Delivery header",
    )
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="GitHub event type e.g. pull_request, check_suite",
    )
    payload_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        doc="Summary metadata of the payload for debugging",
    )
    run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class RunORM(Base):
    """
    Represents an execution run bound to a pull request and commit SHA.
    """

    __tablename__ = "runs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    repo: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Target repo in owner/name format",
    )
    pr_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Pull request number",
    )
    head_sha: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="Git commit SHA bound to this run",
    )
    trigger_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TriggerType.PULL_REQUEST.value,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RunStatus.QUEUED.value,
    )
    policy_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Version of policy evaluated during run",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=Decimal("0.0"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    events: Mapped[list["RunEventORM"]] = relationship(
        "RunEventORM",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="RunEventORM.created_at",
    )
        # Add this relationship to RunORM
    policy_decisions: Mapped[list["PolicyDecisionORM"]] = relationship(
        "PolicyDecisionORM",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="PolicyDecisionORM.created_at",
    )
    approvals: Mapped[list["ApprovalORM"]] = relationship(
        "ApprovalORM",
        back_populates="run",
        cascade="all, delete-orphan",
    )



    __table_args__ = (Index("ix_runs_repo_pr_status", "repo", "pr_number", "status"),)


class RunEventORM(Base):
    """
    Immutable audit log event emitted during run execution.
    """

    __tablename__ = "run_events"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="Agent step: plan, investigate, report, etc.",
    )
    event_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EventType.DECISION.value,
    )
    content: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    run: Mapped["RunORM"] = relationship("RunORM", back_populates="events")

class PolicyORM(Base):
    """
    Persisted security policy configuration per repository with version history.
    """

    __tablename__ = "policies"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    repo: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Repository in owner/name format",
    )
    yaml_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Raw YAML string of the policy",
    )
    rego_bundle: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Compiled Rego policy bundle or compiled data document",
    )
    parsed_content: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        doc="Parsed and validated policy JSON representation",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Monotonically increasing version counter",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class PolicyDecisionORM(Base):
    """
    Immutable audit record of an evaluation decision made for an ActionIntent.
    Forms the backbone of the auditable Action Ledger.
    """

    __tablename__ = "policy_decisions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_intent_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        doc="UUID of the ActionIntent that was evaluated",
    )
    action_requested: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        doc="Snapshot of the ActionIntent payload evaluated",
    )
    rule_matched: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Identifier of the specific policy rule that triggered the verdict",
    )
    risk_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Risk score calculated by RiskEngine (0-100)",
    )
    decision: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="Verdict: ALLOW, DENY, or REQUIRE_APPROVAL",
    )
    policy_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Version of the policy evaluated against",
    )
    opa_query_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        doc="Correlation ID from OPA decision log",
    )
    reason: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
        doc="Human-readable rationale for verdict",
    )
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        doc="Auxiliary diagnostic data from policy evaluation",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    run: Mapped["RunORM"] = relationship("RunORM", back_populates="policy_decisions")

class ProviderHealthORM(Base):
    """
    Periodic health snapshot of upstream LLM providers for observability.
    Captures error rates, latency trends, and circuit states over time.
    """

    __tablename__ = "provider_health"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Provider identifier (gemini, groq, nvidia_nim)",
    )
    model: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        doc="Target model name",
    )
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    request_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    error_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    timeout_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    avg_latency_ms: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    circuit_state: Mapped[str] = mapped_column(
        String(32),
        default="closed",
        nullable=False,
        doc="Circuit state: closed, open, half_open",
    )

    __table_args__ = (
        Index("ix_provider_health_provider_window", "provider", "window_start"),
    )


class ApprovalORM(Base):
    """
    Persisted human approval queue request for sensitive or high-risk actions.
    Tracks reviewer verdicts, serialized action intent, and decision traces.
    """

    __tablename__ = "approvals"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("run_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=ApprovalStatus.PENDING.value,
        nullable=False,
        index=True,
        doc="pending, approved, rejected, expired",
    )
    action_intent: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        doc="Full ActionIntent serialized payload",
    )
    decision_trace: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        doc="OPA rule match, risk score, and budget status trace",
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    decided_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Username or email of the reviewer",
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Rationale provided if rejected",
    )

    # Relationships
    run: Mapped["RunORM"] = relationship("RunORM", back_populates="approvals")

    __table_args__ = (
        Index("ix_approvals_status_requested_at", "status", "requested_at"),
    )

