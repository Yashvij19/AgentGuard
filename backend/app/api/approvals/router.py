"""
REST API router for Human-in-the-Loop approval queue and decision actions.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.approvals.schemas import (
    ApprovalDecisionResponse,
    ApprovalResponse,
    ApproveActionRequest,
    PaginatedApprovalsResponse,
    RejectActionRequest,
)
from app.api.dependencies import get_approval_service
from app.domain.exceptions import ApprovalNotFoundError
from app.services.approval_service import ApprovalService

router = APIRouter(prefix="/api/approvals", tags=["Approvals"])


@router.get(
    "",
    response_model=PaginatedApprovalsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Pending Approvals",
    description="Retrieve a FIFO queue of actions awaiting human review, oldest first.",
)
async def list_pending_approvals(
    approval_service: Annotated[ApprovalService, Depends(get_approval_service)],
    limit: Annotated[int, Query(ge=1, le=100, description="Max items to return")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    repo: Annotated[str | None, Query(description="Filter by repository (owner/name)")] = None,
) -> PaginatedApprovalsResponse:
    """Fetch pending approvals queue."""
    approvals = await approval_service.list_pending(limit=limit, offset=offset, repo=repo)
    items = [ApprovalResponse.model_validate(a, from_attributes=True) for a in approvals]

    return PaginatedApprovalsResponse(
        items=items,
        total=len(items),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{approval_id}",
    response_model=ApprovalResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Approval Detail",
    description="Retrieve full details for an approval request including ActionIntent and decision trace.",
)
async def get_approval_detail(
    approval_id: UUID,
    approval_service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> ApprovalResponse:
    """Fetch specific approval detail."""
    approval = await approval_service.get_approval(approval_id)
    if not approval:
        raise ApprovalNotFoundError(f"Approval '{approval_id}' not found.")

    return ApprovalResponse.model_validate(approval, from_attributes=True)


@router.post(
    "/{approval_id}/approve",
    response_model=ApprovalDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve Action",
    description="Approve a pending action and dispatch it for execution.",
)
async def approve_action(
    approval_id: UUID,
    body: ApproveActionRequest,
    approval_service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> ApprovalDecisionResponse:
    """Approve a pending action."""
    result = await approval_service.approve(
        approval_id=approval_id,
        decided_by=body.decided_by,
        execute_action=body.execute,
    )
    return ApprovalDecisionResponse.model_validate(result, from_attributes=True)


@router.post(
    "/{approval_id}/reject",
    response_model=ApprovalDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject Action",
    description="Reject a pending action with an explanatory reason.",
)
async def reject_action(
    approval_id: UUID,
    body: RejectActionRequest,
    approval_service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> ApprovalDecisionResponse:
    """Reject a pending action."""
    result = await approval_service.reject(
        approval_id=approval_id,
        decided_by=body.decided_by,
        reason=body.reason,
    )
    return ApprovalDecisionResponse.model_validate(result, from_attributes=True)
