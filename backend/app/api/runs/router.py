"""
API router for listing and inspecting AgentGuard execution runs.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_event_repository, get_run_repository
from app.api.runs.schemas import (
    PaginatedRunsResponse,
    RunDetailResponse,
    RunEventResponse,
    RunResponse,
)
from app.domain.exceptions import RunNotFoundError
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.run_repository import RunRepository

router = APIRouter(prefix="/api/runs", tags=["Runs"])


@router.get(
    "",
    response_model=PaginatedRunsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Runs",
    description="Retrieve a paginated list of agent runs ordered chronologically by newest first.",
)
async def list_runs(
    run_repo: Annotated[RunRepository, Depends(get_run_repository)],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of runs to return")] = 20,
    offset: Annotated[int, Query(ge=0, description="Offset for pagination")] = 0,
) -> PaginatedRunsResponse:
    """Fetch paginated runs collection."""
    runs = await run_repo.list_runs(limit=limit, offset=offset)
    items = [RunResponse.model_validate(run, from_attributes=True) for run in runs]

    return PaginatedRunsResponse(
        items=items,
        total=len(items),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{run_id}",
    response_model=RunDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Run Detail",
    description="Retrieve a specific run along with its chronological audit event timeline.",
)
async def get_run(
    run_id: UUID,
    run_repo: Annotated[RunRepository, Depends(get_run_repository)],
    event_repo: Annotated[EventRepository, Depends(get_event_repository)],
) -> RunDetailResponse:
    """Fetch run details and event audit trail."""
    run = await run_repo.get_by_id(run_id)
    if not run:
        raise RunNotFoundError(f"Run '{run_id}' not found.")

    events = await event_repo.get_events_for_run(run_id)

    return RunDetailResponse(
        run=RunResponse.model_validate(run, from_attributes=True),
        events=[RunEventResponse.model_validate(event, from_attributes=True) for event in events],
    )
