"""
SQLAlchemy 2.0 ORM models for AgentGuard.
Defines persistent schema for runs, webhook idempotency, and audit trails.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
