"""
Repository for recording and querying LLM provider health metrics.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.provider_health import CircuitState, ProviderHealth
from app.infrastructure.database.models import ProviderHealthORM


class ProviderHealthRepository:
    """
    Data access layer for provider reliability metrics.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_snapshot(self, health: ProviderHealth) -> ProviderHealth:
        """Persist a new provider health snapshot."""
        orm = ProviderHealthORM(
            id=health.id,
            provider=health.provider,
            model=health.model,
            window_start=health.window_start,
            request_count=health.request_count,
            error_count=health.error_count,
            timeout_count=health.timeout_count,
            avg_latency_ms=health.avg_latency_ms,
            circuit_state=health.circuit_state.value,
        )
        self.session.add(orm)
        await self.session.commit()
        await self.session.refresh(orm)
        return self._to_domain(orm)

    async def get_latest(self, provider: str, model: str | None = None) -> ProviderHealth | None:
        """Fetch the most recent health snapshot for a provider."""
        stmt = select(ProviderHealthORM).where(ProviderHealthORM.provider == provider)
        if model:
            stmt = stmt.where(ProviderHealthORM.model == model)
        stmt = stmt.order_by(desc(ProviderHealthORM.window_start)).limit(1)

        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_recent_history(
        self,
        provider: str,
        since_hours: int = 24,
    ) -> list[ProviderHealth]:
        """Fetch historical health snapshots for analysis and dashboards."""
        since = datetime.now(UTC) - timedelta(hours=since_hours)
        stmt = (
            select(ProviderHealthORM)
            .where(
                ProviderHealthORM.provider == provider,
                ProviderHealthORM.window_start >= since,
            )
            .order_by(desc(ProviderHealthORM.window_start))
        )
        result = await self.session.execute(stmt)
        orms: Sequence[ProviderHealthORM] = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    @staticmethod
    def _to_domain(orm: ProviderHealthORM) -> ProviderHealth:
        return ProviderHealth(
            id=orm.id,
            provider=orm.provider,
            model=orm.model,
            window_start=orm.window_start,
            request_count=orm.request_count,
            error_count=orm.error_count,
            timeout_count=orm.timeout_count,
            avg_latency_ms=orm.avg_latency_ms,
            circuit_state=CircuitState(orm.circuit_state),
        )
