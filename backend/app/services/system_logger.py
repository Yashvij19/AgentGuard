"""
Centralized Developer System Logger for AgentGuard.
Provides a universal, developer-friendly logging method across all services.
Usage:
    from app.services.system_logger import system_logger
    await system_logger.info(
        message="Evaluating capability github.create_commit",
        source="policy_gateway",
        api_name="evaluate_intent",
        task_progress="Phase 4/6: Patch",
        commit_sha=run.head_sha,
        status="PASS",
        extra={"rule_matched": "capability_requires_approval"}
    )
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import SystemLogORM

logger = structlog.get_logger(__name__)


class SystemLogger:
    """Universal logging service that persists structured developer logs to PostgreSQL."""

    def __init__(self, session_factory=None) -> None:
        self._session_factory = session_factory

    def set_session_factory(self, session_factory) -> None:
        """Bind session factory for autonomous background writes."""
        self._session_factory = session_factory

    async def log(
        self,
        level: str,
        message: str,
        source: str = "core",
        api_name: str | None = None,
        task_progress: str | None = None,
        commit_sha: str | None = None,
        pr_number: int | None = None,
        repo: str | None = None,
        run_id: UUID | None = None,
        status: str = "PASS",
        latency_ms: int = 0,
        extra: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> SystemLogORM | None:
        """
        Record a structured developer log.
        Saves to PostgreSQL with automatic 24-hour expiration timestamp.
        """
        log_entry = SystemLogORM(
            timestamp=datetime.now(UTC),
            level=level.upper(),
            source=source,
            api_name=api_name,
            message=message,
            task_progress=task_progress,
            status=status.upper(),
            commit_sha=commit_sha.strip().lower() if commit_sha else None,
            pr_number=pr_number,
            repo=repo,
            run_id=run_id,
            latency_ms=latency_ms,
            extra_info=extra or {},
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )

        try:
            if session:
                session.add(log_entry)
                await session.flush()
                return log_entry

            if self._session_factory:
                async with self._session_factory() as local_session:
                    local_session.add(log_entry)
                    await local_session.commit()
                    return log_entry
        except Exception as err:
            logger.warning("system_logger_failed_to_persist", error=str(err), msg=message)

        return None

    async def info(
        self,
        message: str,
        source: str = "core",
        **kwargs: Any,
    ) -> SystemLogORM | None:
        """Record an INFO level developer log."""
        return await self.log(level="INFO", message=message, source=source, **kwargs)

    async def warning(
        self,
        message: str,
        source: str = "core",
        **kwargs: Any,
    ) -> SystemLogORM | None:
        """Record a WARNING level developer log."""
        return await self.log(level="WARNING", message=message, source=source, status="WAITING", **kwargs)

    async def error(
        self,
        message: str,
        source: str = "core",
        **kwargs: Any,
    ) -> SystemLogORM | None:
        """Record an ERROR level developer log."""
        return await self.log(level="ERROR", message=message, source=source, status="FAIL", **kwargs)

    async def debug(
        self,
        message: str,
        source: str = "core",
        **kwargs: Any,
    ) -> SystemLogORM | None:
        """Record a DEBUG level developer log."""
        return await self.log(level="DEBUG", message=message, source=source, **kwargs)


# Global singleton instance for easy import across modules
system_logger = SystemLogger()
