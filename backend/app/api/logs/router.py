"""
API Router for developer system logs.
Provides inspection, per-SHA filtering, manual logging, and retention cleanup.
"""

from typing import Annotated, Any
from uuid import UUID


from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import DbSessionDep
from app.api.logs.schemas import CreateLogRequest, PaginatedLogsResponse, SystemLogItem
from app.container import container
from app.services.system_logger import system_logger

router = APIRouter(prefix="/api/logs", tags=["Logs"])


@router.get(
    "",
    response_model=PaginatedLogsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Developer System Logs",
    description="Retrieve structured developer logs with filtering by commit SHA, log level, source subsystem, and text search.",
)
async def list_logs(
    session: DbSessionDep,
    commit_sha: Annotated[str | None, Query(description="Filter by PR commit SHA")] = None,
    level: Annotated[str | None, Query(description="Filter by log level (INFO, WARNING, ERROR, DEBUG)")] = None,
    source: Annotated[str | None, Query(description="Filter by originating subsystem")] = None,
    status_filter: Annotated[str | None, Query(alias="status", description="Filter by status (PASS, FAIL, WAITING, RUNNING)")] = None,
    search: Annotated[str | None, Query(description="Full text search in message or API name")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Page limit")] = 100,
    offset: Annotated[int, Query(ge=0, description="Offset for pagination")] = 0,
) -> PaginatedLogsResponse:
    """Fetch paginated, filtered developer system logs."""
    log_repo = container.get_log_repository(session)
    logs, total = await log_repo.list_logs(
        commit_sha=commit_sha,
        level=level,
        source=source,
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )
    await session.commit()

    items = [
        SystemLogItem(
            id=log.id,
            timestamp=log.timestamp,
            level=log.level,
            source=log.source,
            api_name=log.api_name,
            message=log.message,
            task_progress=log.task_progress,
            status=log.status,
            commit_sha=log.commit_sha,
            pr_number=log.pr_number,
            repo=log.repo,
            run_id=log.run_id,
            latency_ms=log.latency_ms,
            extra_info=log.extra_info,
            expires_at=log.expires_at,
        )
        for log in logs
    ]

    return PaginatedLogsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=SystemLogItem,
    status_code=status.HTTP_201_CREATED,
    summary="Record Developer System Log",
    description="Record a custom developer or runtime log in PostgreSQL with automatic 24-hour expiration.",
)
async def create_log(
    body: CreateLogRequest,
    session: DbSessionDep,
) -> SystemLogItem:
    """Create a new developer system log."""
    log_entry = await system_logger.log(
        level=body.level,
        message=body.message,
        source=body.source,
        api_name=body.api_name,
        task_progress=body.task_progress,
        commit_sha=body.commit_sha,
        pr_number=body.pr_number,
        repo=body.repo,
        run_id=body.run_id,
        status=body.status,
        latency_ms=body.latency_ms,
        extra=body.extra_info,
        session=session,
    )
    await session.commit()

    if not log_entry:
        raise RuntimeError("Failed to persist developer log entry.")

    return SystemLogItem(
        id=log_entry.id,
        timestamp=log_entry.timestamp,
        level=log_entry.level,
        source=log_entry.source,
        api_name=log_entry.api_name,
        message=log_entry.message,
        task_progress=log_entry.task_progress,
        status=log_entry.status,
        commit_sha=log_entry.commit_sha,
        pr_number=log_entry.pr_number,
        repo=log_entry.repo,
        run_id=log_entry.run_id,
        latency_ms=log_entry.latency_ms,
        extra_info=log_entry.extra_info,
        expires_at=log_entry.expires_at,
    )


@router.delete(
    "/{log_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Single Log Entry",
    description="Manually delete an individual developer log record.",
)
async def delete_log(
    log_id: UUID,
    session: DbSessionDep,
) -> dict[str, Any]:
    """Delete a single log entry."""
    log_repo = container.get_log_repository(session)
    deleted = await log_repo.delete(log_id)
    await session.commit()
    return {"success": deleted, "deleted_id": str(log_id)}


@router.delete(
    "",
    status_code=status.HTTP_200_OK,
    summary="Purge Developer System Logs",
    description="Purge all developer logs, or all logs belonging to a specific commit SHA.",
)
async def purge_logs(
    session: DbSessionDep,
    commit_sha: Annotated[str | None, Query(description="Purge only logs matching this commit SHA")] = None,
) -> dict[str, Any]:
    """Bulk purge developer logs."""
    log_repo = container.get_log_repository(session)
    count = await log_repo.delete_all(commit_sha=commit_sha)
    await session.commit()
    return {"success": True, "purged_count": count, "commit_sha": commit_sha}
