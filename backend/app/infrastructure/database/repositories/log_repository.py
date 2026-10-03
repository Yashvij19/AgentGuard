"""
Log repository for persisting and querying developer system logs.
Includes automatic expiration handling (24h retention) and per-SHA filtering.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import SystemLogORM


class LogRepository:
    """Repository handling CRUD operations and TTL cleanup for system_logs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, log: SystemLogORM) -> SystemLogORM:
        """Persist a new developer system log entry."""
        self._session.add(log)
        await self._session.flush()
        return log

    async def cleanup_expired(self) -> int:
        """Purge system logs whose expires_at timestamp has elapsed."""
        now = datetime.now(UTC)
        stmt = delete(SystemLogORM).where(SystemLogORM.expires_at <= now)
        res = await self._session.execute(stmt)
        return int(res.rowcount or 0)

    async def list_logs(
        self,
        commit_sha: str | None = None,
        level: str | None = None,
        source: str | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[SystemLogORM], int]:
        """
        List developer logs with filtering and total count.
        Automatically cleans up expired logs on query.
        """
        # Purge expired records first
        await self.cleanup_expired()

        query = select(SystemLogORM)
        count_query = select(func.count()).select_from(SystemLogORM)

        filters = []
        if commit_sha:
            clean_sha = commit_sha.strip().lower()
            filters.append(
                or_(
                    SystemLogORM.commit_sha.ilike(f"{clean_sha}%"),
                    SystemLogORM.commit_sha == clean_sha,
                )
            )

        if level and level.upper() != "ALL":
            filters.append(SystemLogORM.level == level.upper())

        if source and source.lower() != "all":
            filters.append(SystemLogORM.source.ilike(f"%{source}%"))

        if status and status.upper() != "ALL":
            filters.append(SystemLogORM.status == status.upper())

        if search:
            s = f"%{search.strip()}%"
            filters.append(
                or_(
                    SystemLogORM.message.ilike(s),
                    SystemLogORM.api_name.ilike(s),
                    SystemLogORM.task_progress.ilike(s),
                )
            )

        if filters:
            query = query.where(*filters)
            count_query = count_query.where(*filters)

        # Ordering: newest first
        query = query.order_by(SystemLogORM.timestamp.desc()).limit(limit).offset(offset)

        total_res = await self._session.execute(count_query)
        total = total_res.scalar() or 0

        logs_res = await self._session.execute(query)
        logs = list(logs_res.scalars().all())

        return logs, total

    async def get_by_id(self, log_id: UUID) -> SystemLogORM | None:
        """Fetch a single log entry by its UUID."""
        stmt = select(SystemLogORM).where(SystemLogORM.id == log_id)
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def delete(self, log_id: UUID) -> bool:
        """Delete an individual log entry."""
        stmt = delete(SystemLogORM).where(SystemLogORM.id == log_id)
        res = await self._session.execute(stmt)
        return bool(res.rowcount and res.rowcount > 0)

    async def delete_all(self, commit_sha: str | None = None) -> int:
        """Purge all logs, or all logs belonging to a specific commit SHA."""
        stmt = delete(SystemLogORM)
        if commit_sha:
            stmt = stmt.where(
                or_(
                    SystemLogORM.commit_sha.ilike(f"{commit_sha}%"),
                    SystemLogORM.commit_sha == commit_sha,
                )
            )
        res = await self._session.execute(stmt)
        return int(res.rowcount or 0)
