"""
Repository for managing Run lifecycles and query operations.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import RunNotFoundError
from app.domain.models.run import Run, RunStatus, TriggerType
from app.infrastructure.database.models import RunORM


class RunRepository:
    """
    Manages persistence and status transitions for Agent execution runs.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: Run) -> Run:
        """Persist a newly initialized run."""
        orm = self._to_orm(run)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get_by_id(self, run_id: UUID) -> Run | None:
        """Fetch a run by primary key UUID."""
        stmt = select(RunORM).where(RunORM.id == run_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_active_run_for_pr(self, repo: str, pr_number: int) -> Run | None:
        """
        Check if there is an ongoing (queued, running, or paused) run for this PR.
        Used by the RunCoordinator to prevent concurrent overlapping executions.
        """
        active_statuses = [
            RunStatus.QUEUED.value,
            RunStatus.RUNNING.value,
            RunStatus.PAUSED.value,
        ]
        stmt = (
            select(RunORM)
            .where(
                RunORM.repo == repo,
                RunORM.pr_number == pr_number,
                RunORM.status.in_(active_statuses),
            )
            .order_by(RunORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        orm = result.scalars().first()
        return self._to_domain(orm) if orm else None

    async def update_status(
        self,
        run_id: UUID,
        status: RunStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> Run:
        """Update run execution status and lifecycle timestamps."""
        stmt = select(RunORM).where(RunORM.id == run_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            raise RunNotFoundError(f"Run '{run_id}' not found.")

        orm.status = status.value
        if started_at is not None:
            orm.started_at = started_at
        if completed_at is not None:
            orm.completed_at = completed_at
        orm.updated_at = datetime.now(UTC)

        await self._session.flush()
        return self._to_domain(orm)

    async def mark_stale(self, run_id: UUID) -> Run:
        """Mark an existing run as stale when a newer commit arrives."""
        return await self.update_status(
            run_id=run_id,
            status=RunStatus.STALE,
            completed_at=datetime.now(UTC),
        )

    async def list_runs(self, limit: int = 50, offset: int = 0) -> list[Run]:
        """Fetch paginated list of runs ordered newest first."""
        stmt = select(RunORM).order_by(RunORM.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    @staticmethod
    def _to_orm(run: Run) -> RunORM:
        """Convert pure domain Run model to SQLAlchemy RunORM."""
        return RunORM(
            id=run.id,
            repo=run.repo,
            pr_number=run.pr_number,
            head_sha=run.head_sha,
            trigger_type=run.trigger_type.value,
            status=run.status.value,
            policy_version=run.policy_version,
            started_at=run.started_at,
            completed_at=run.completed_at,
            total_tokens=run.total_tokens,
            total_cost_usd=run.total_cost_usd,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    @staticmethod
    def _to_domain(orm: RunORM) -> Run:
        """Convert SQLAlchemy RunORM to pure domain Run model."""
        return Run(
            id=orm.id,
            repo=orm.repo,
            pr_number=orm.pr_number,
            head_sha=orm.head_sha,
            trigger_type=TriggerType(orm.trigger_type),
            status=RunStatus(orm.status),
            policy_version=orm.policy_version,
            started_at=orm.started_at,
            completed_at=orm.completed_at,
            total_tokens=orm.total_tokens,
            total_cost_usd=orm.total_cost_usd,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
