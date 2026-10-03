"""
Repository for managing Run lifecycles and query operations.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
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

    async def add_tokens_and_cost(
        self,
        run_id: UUID,
        tokens: int,
        cost_usd: Decimal,
    ) -> Run:
        """Increment tokens and cost accounting for an active run."""
        stmt = select(RunORM).where(RunORM.id == run_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            raise RunNotFoundError(f"Run '{run_id}' not found.")

        orm.total_tokens = int(orm.total_tokens or 0) + tokens
        orm.total_cost_usd = Decimal(str(orm.total_cost_usd or Decimal("0.0000"))) + cost_usd
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
        try:
            trigger_type = TriggerType(orm.trigger_type)
        except ValueError:
            trigger_type = TriggerType.PULL_REQUEST

        try:
            status = RunStatus(orm.status)
        except ValueError:
            status = RunStatus.QUEUED

        return Run(
            id=orm.id,
            repo=orm.repo,
            pr_number=orm.pr_number,
            head_sha=orm.head_sha,
            trigger_type=trigger_type,
            status=status,
            policy_version=orm.policy_version,
            started_at=orm.started_at,
            completed_at=orm.completed_at,
            total_tokens=orm.total_tokens,
            total_cost_usd=orm.total_cost_usd,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def get_aggregate_stats(self) -> dict[str, Any]:
        """Calculate high-level performance and cost metrics across all runs."""
        stmt = select(
            func.count(RunORM.id).label("total"),
            func.count(RunORM.id)
            .filter(RunORM.status == RunStatus.COMPLETED.value)
            .label("completed"),
            func.count(RunORM.id).filter(RunORM.status == RunStatus.FAILED.value).label("failed"),
            func.count(RunORM.id).filter(RunORM.status == RunStatus.PAUSED.value).label("paused"),
            func.coalesce(func.sum(RunORM.total_cost_usd), Decimal("0.000000")).label("total_cost"),
            func.coalesce(func.sum(RunORM.total_tokens), 0).label("total_tokens"),
        )
        result = await self._session.execute(stmt)
        row = result.one()
        total = row.total or 0
        completed = row.completed or 0
        success_rate = (completed / total * 100.0) if total > 0 else 0.0
        return {
            "total_runs": total,
            "completed_runs": completed,
            "failed_runs": row.failed or 0,
            "paused_runs": row.paused or 0,
            "success_rate_percent": round(success_rate, 1),
            "total_cost_usd": row.total_cost,
            "total_tokens": int(row.total_tokens or 0),
            "avg_duration_seconds": 0.0,
        }

    async def get_hourly_outcomes(self) -> list[dict[str, Any]]:
        """
        Aggregate runs over the last 24 hours into 12 2-hour rolling intervals.
        Returns actual counts of completed, paused, and failed runs per bucket.
        If no runs exist, returns zeroed buckets for the 12 time windows.
        """
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=24)
        stmt = select(RunORM).where(RunORM.created_at >= cutoff)
        result = await self._session.execute(stmt)
        runs = result.scalars().all()

        current_even_hour = now.replace(minute=0, second=0, microsecond=0)
        if current_even_hour.hour % 2 != 0:
            current_even_hour -= timedelta(hours=1)

        buckets: list[dict[str, Any]] = []
        for i in range(11, -1, -1):
            b_start = current_even_hour - timedelta(hours=2 * i)
            b_end = b_start + timedelta(hours=2)
            time_label = b_start.strftime("%H:00")

            def is_in_bucket(r: RunORM, start: datetime = b_start, end: datetime = b_end) -> bool:
                r_dt = r.created_at if r.created_at.tzinfo is not None else r.created_at.replace(tzinfo=UTC)
                return start <= r_dt < end

            comp = sum(1 for r in runs if is_in_bucket(r) and r.status == RunStatus.COMPLETED.value)
            pause = sum(1 for r in runs if is_in_bucket(r) and r.status == RunStatus.PAUSED.value)
            fail = sum(1 for r in runs if is_in_bucket(r) and r.status == RunStatus.FAILED.value)

            buckets.append({
                "time": time_label,
                "completed": comp,
                "paused": pause,
                "failed": fail,
                "active": (i == 0),
            })

        return buckets
