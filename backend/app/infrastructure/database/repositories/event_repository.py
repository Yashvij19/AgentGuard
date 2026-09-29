"""
Repository for recording and reading append-only execution events.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.run_event import EventType, RunEvent
from app.infrastructure.database.models import RunEventORM


class EventRepository:
    """
    Manages the append-only audit trail of Run events (decisions, tool calls, logs).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: RunEvent) -> RunEvent:
        """Record a new immutable event into the run timeline."""
        orm = RunEventORM(
            id=event.id,
            run_id=event.run_id,
            step_name=event.step_name,
            event_type=event.event_type.value,
            content=event.content,
            tokens_used=event.tokens_used,
            latency_ms=event.latency_ms,
            created_at=event.created_at,
        )
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def get_events_for_run(self, run_id: UUID) -> list[RunEvent]:
        """Fetch all audit events for a given run in chronological order."""
        stmt = (
            select(RunEventORM)
            .where(RunEventORM.run_id == run_id)
            .order_by(RunEventORM.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    # Convenience alias matching repository naming conventions
    get_by_run_id = get_events_for_run


    @staticmethod
    def _to_domain(orm: RunEventORM) -> RunEvent:
        """Map internal SQLAlchemy ORM to pure domain RunEvent model."""
        return RunEvent(
            id=orm.id,
            run_id=orm.run_id,
            step_name=orm.step_name,
            event_type=EventType(orm.event_type),
            content=orm.content,
            tokens_used=orm.tokens_used,
            latency_ms=orm.latency_ms,
            created_at=orm.created_at,
        )
