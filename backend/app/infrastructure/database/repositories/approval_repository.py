"""
Repository for managing Human-in-the-Loop Approval queue persistence and queries.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import ApprovalNotFoundError, InvalidApprovalStateError
from app.domain.models.approval import Approval, ApprovalStatus
from app.infrastructure.database.models import ApprovalORM, RunORM


class ApprovalRepository:
    """
    Persistence layer for approval requests, reviewer decisions, and timeout expiration.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, approval: Approval) -> Approval:
        """Persist a new pending approval request."""
        orm = self._to_orm(approval)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get_by_id(self, approval_id: UUID) -> Approval | None:
        """Fetch an approval by its primary key UUID."""
        stmt = select(ApprovalORM).where(ApprovalORM.id == approval_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_run_id(self, run_id: UUID) -> list[Approval]:
        """Fetch all approval requests for a specific run, newest first."""
        stmt = (
            select(ApprovalORM)
            .where(ApprovalORM.run_id == run_id)
            .order_by(ApprovalORM.requested_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_pending_for_run(self, run_id: UUID) -> Approval | None:
        """Fetch the current active pending approval for a run (if any)."""
        stmt = (
            select(ApprovalORM)
            .where(
                ApprovalORM.run_id == run_id,
                ApprovalORM.status == ApprovalStatus.PENDING.value,
            )
            .order_by(ApprovalORM.requested_at.desc())
        )
        result = await self._session.execute(stmt)
        orm = result.scalars().first()
        return self._to_domain(orm) if orm else None

    async def list_pending(
        self,
        limit: int = 50,
        offset: int = 0,
        repo: str | None = None,
    ) -> list[Approval]:
        """
        List pending approvals ordered by arrival time (FIFO: oldest first).
        Optionally filter by repository via joined Run table.
        """
        stmt = select(ApprovalORM).where(ApprovalORM.status == ApprovalStatus.PENDING.value)

        if repo:
            stmt = stmt.join(RunORM, ApprovalORM.run_id == RunORM.id).where(RunORM.repo == repo)

        stmt = stmt.order_by(ApprovalORM.requested_at.asc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def update_decision(
        self,
        approval_id: UUID,
        status: ApprovalStatus,
        decided_by: str,
        rejection_reason: str | None = None,
    ) -> Approval:
        """
        Transition an approval from PENDING to APPROVED or REJECTED.
        Enforces that only PENDING requests can be decided.
        """
        stmt = select(ApprovalORM).where(ApprovalORM.id == approval_id).with_for_update()
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if not orm:
            raise ApprovalNotFoundError(f"Approval '{approval_id}' not found.")

        if orm.status != ApprovalStatus.PENDING.value:
            raise InvalidApprovalStateError(
                f"Cannot decide approval '{approval_id}' with existing status '{orm.status}'."
            )

        orm.status = status.value
        orm.decided_by = decided_by
        orm.decided_at = datetime.now(UTC)
        orm.rejection_reason = rejection_reason

        await self._session.flush()
        return self._to_domain(orm)

    async def expire_stale_approvals(self, timeout_seconds: int = 1800) -> list[Approval]:
        """
        Scan and mark all PENDING approvals older than timeout_seconds as EXPIRED.
        Default timeout: 1800 seconds (30 minutes).
        """
        cutoff = datetime.now(UTC) - timedelta(seconds=timeout_seconds)
        stmt = select(ApprovalORM).where(
            ApprovalORM.status == ApprovalStatus.PENDING.value,
            ApprovalORM.requested_at <= cutoff,
        )
        result = await self._session.execute(stmt)
        stale_records = list(result.scalars().all())

        expired_domains: list[Approval] = []
        now = datetime.now(UTC)
        for orm in stale_records:
            orm.status = ApprovalStatus.EXPIRED.value
            orm.decided_at = now
            expired_domains.append(self._to_domain(orm))

        if stale_records:
            await self._session.flush()

        return expired_domains

    @staticmethod
    def _to_domain(orm: ApprovalORM) -> Approval:
        """Convert SQLAlchemy ORM row to domain entity."""
        return Approval(
            id=orm.id,
            run_id=orm.run_id,
            event_id=orm.event_id,
            status=ApprovalStatus(orm.status),
            action_intent=orm.action_intent,
            decision_trace=orm.decision_trace,
            requested_at=orm.requested_at,
            decided_at=orm.decided_at,
            decided_by=orm.decided_by,
            rejection_reason=orm.rejection_reason,
        )

    @staticmethod
    def _to_orm(domain: Approval) -> ApprovalORM:
        """Convert domain entity to SQLAlchemy ORM model."""
        return ApprovalORM(
            id=domain.id,
            run_id=domain.run_id,
            event_id=domain.event_id,
            status=domain.status.value,
            action_intent=domain.action_intent,
            decision_trace=domain.decision_trace,
            requested_at=domain.requested_at,
            decided_at=domain.decided_at,
            decided_by=domain.decided_by,
            rejection_reason=domain.rejection_reason,
        )
