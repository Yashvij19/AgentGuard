"""
Integration tests for the Approvals REST API: listing, detail, approve, and reject.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_approval_service
from app.domain.models.approval import Approval, ApprovalDecisionResult, ApprovalStatus
from app.main import app
from app.services.approval_service import ApprovalService


@pytest.fixture
def mock_approval_service() -> AsyncMock:
    return AsyncMock(spec=ApprovalService)


async def test_list_pending_approvals_endpoint(
    test_client: AsyncClient,
    mock_approval_service: AsyncMock,
) -> None:
    """GET /api/approvals returns list of pending requests."""
    app.dependency_overrides[get_approval_service] = lambda: mock_approval_service

    approval_id = uuid4()
    run_id = uuid4()
    mock_approval = Approval(
        id=approval_id,
        run_id=run_id,
        status=ApprovalStatus.PENDING,
        action_intent={"action": "file_write", "target": "prod.yaml"},
        decision_trace={"risk_score": 65},
    )
    mock_approval_service.list_pending.return_value = [mock_approval]

    try:
        response = await test_client.get("/api/approvals?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == str(approval_id)
        assert data["items"][0]["status"] == "pending"
    finally:
        app.dependency_overrides.pop(get_approval_service, None)


async def test_get_approval_detail_not_found(
    test_client: AsyncClient,
    mock_approval_service: AsyncMock,
) -> None:
    """GET /api/approvals/{id} returns 404 when ID does not exist."""
    app.dependency_overrides[get_approval_service] = lambda: mock_approval_service
    missing_id = uuid4()
    mock_approval_service.get_approval.return_value = None

    try:
        response = await test_client.get(f"/api/approvals/{missing_id}")
        assert response.status_code == 404
        assert response.json()["error"] == "ApprovalNotFoundError"
    finally:
        app.dependency_overrides.pop(get_approval_service, None)


async def test_approve_action_endpoint(
    test_client: AsyncClient,
    mock_approval_service: AsyncMock,
) -> None:
    """POST /api/approvals/{id}/approve grants approval and dispatches action."""
    app.dependency_overrides[get_approval_service] = lambda: mock_approval_service

    approval_id = uuid4()
    run_id = uuid4()
    mock_result = ApprovalDecisionResult(
        approval_id=approval_id,
        run_id=run_id,
        status=ApprovalStatus.APPROVED,
        decided_by="senior_dev",
        action_executed=True,
        message="Action approved and executed",
    )
    mock_approval_service.approve.return_value = mock_result

    try:
        payload = {"decided_by": "senior_dev", "execute": True}
        response = await test_client.post(f"/api/approvals/{approval_id}/approve", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["action_executed"] is True
        assert data["decided_by"] == "senior_dev"
    finally:
        app.dependency_overrides.pop(get_approval_service, None)


async def test_reject_action_endpoint(
    test_client: AsyncClient,
    mock_approval_service: AsyncMock,
) -> None:
    """POST /api/approvals/{id}/reject declines action with reason."""
    app.dependency_overrides[get_approval_service] = lambda: mock_approval_service

    approval_id = uuid4()
    run_id = uuid4()
    mock_result = ApprovalDecisionResult(
        approval_id=approval_id,
        run_id=run_id,
        status=ApprovalStatus.REJECTED,
        decided_by="security_auditor",
        action_executed=False,
        message="Action rejected: Dangerous path",
    )
    mock_approval_service.reject.return_value = mock_result

    try:
        payload = {"decided_by": "security_auditor", "reason": "Dangerous path"}
        response = await test_client.post(f"/api/approvals/{approval_id}/reject", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["action_executed"] is False
    finally:
        app.dependency_overrides.pop(get_approval_service, None)
