"""
Integration tests for AgentGuard Phase 1 HTTP endpoints.
Tests the full HTTP pipeline: Webhook Ingestion -> Run Creation -> Detail & Health APIs.
"""

import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.dependencies import (
    get_event_repository,
    get_run_repository,
    get_webhook_service,
)
from app.config import settings
from app.domain.exceptions import DuplicateDeliveryError
from app.domain.models.run import RunStatus
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.run_repository import RunRepository
from app.main import app
from app.services.webhook_service import WebhookService
from tests.factories import (
    compute_webhook_signature,
    create_test_event,
    create_test_run,
    create_test_webhook_payload,
)


@pytest.mark.asyncio
async def test_post_webhook_triggers_run_accepted(test_client: AsyncClient) -> None:
    """Posting a valid PR opened webhook must return HTTP 202 Accepted with the run ID."""
    test_run = create_test_run(status=RunStatus.QUEUED)

    mock_service = AsyncMock(spec=WebhookService)
    mock_service.handle_github_webhook = AsyncMock(return_value=test_run)

    app.dependency_overrides[get_webhook_service] = lambda: mock_service

    try:
        payload_dict = create_test_webhook_payload(action="opened", pr_number=42)
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = compute_webhook_signature(payload_bytes, settings.github_webhook_secret)

        response = await test_client.post(
            "/webhooks/github",
            content=payload_bytes,
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Delivery": "delivery-int-1",
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "accepted"
        assert body["run_id"] == str(test_run.id)
        assert body["delivery_id"] == "delivery-int-1"
        assert "X-Request-ID" in response.headers
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_duplicate_webhook_returns_200_ignored(test_client: AsyncClient) -> None:
    """Duplicate webhook delivery must return HTTP 200 with status 'ignored' (idempotency)."""
    mock_service = AsyncMock(spec=WebhookService)
    mock_service.handle_github_webhook.side_effect = DuplicateDeliveryError(
        "Webhook delivery 'delivery-dup-int' has already been processed."
    )

    app.dependency_overrides[get_webhook_service] = lambda: mock_service

    try:
        payload_bytes = b'{"action": "opened"}'
        signature = compute_webhook_signature(payload_bytes, settings.github_webhook_secret)

        response = await test_client.post(
            "/webhooks/github",
            content=payload_bytes,
            headers={
                "X-Hub-Signature-256": signature,
                "X-GitHub-Delivery": "delivery-dup-int",
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ignored"
        assert "already been processed" in body["message"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_runs_and_run_detail(test_client: AsyncClient) -> None:
    """GET /api/runs and GET /api/runs/{run_id} return paginated items and event timelines."""
    run_1 = create_test_run(pr_number=10)
    event_1 = create_test_event(run_id=run_1.id, step_name="plan")

    mock_run_repo = AsyncMock(spec=RunRepository)
    mock_run_repo.list_runs = AsyncMock(return_value=[run_1])
    mock_run_repo.get_by_id = AsyncMock(
        side_effect=lambda r_id: run_1 if r_id == run_1.id else None
    )

    mock_event_repo = AsyncMock(spec=EventRepository)
    mock_event_repo.get_events_for_run = AsyncMock(return_value=[event_1])

    app.dependency_overrides[get_run_repository] = lambda: mock_run_repo
    app.dependency_overrides[get_event_repository] = lambda: mock_event_repo

    try:
        # 1. List runs
        list_resp = await test_client.get("/api/runs?limit=10&offset=0")
        assert list_resp.status_code == 200
        list_body = list_resp.json()
        assert len(list_body["items"]) == 1
        assert list_body["items"][0]["id"] == str(run_1.id)

        # 2. Get run detail with events
        detail_resp = await test_client.get(f"/api/runs/{run_1.id}")
        assert detail_resp.status_code == 200
        detail_body = detail_resp.json()
        assert detail_body["run"]["id"] == str(run_1.id)
        assert len(detail_body["events"]) == 1
        assert detail_body["events"][0]["step_name"] == "plan"

        # 3. Non-existent run returns 404
        missing_id = uuid4()
        not_found_resp = await test_client.get(f"/api/runs/{missing_id}")
        assert not_found_resp.status_code == 404
        assert not_found_resp.json()["error"] == "RunNotFoundError"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_endpoint(test_client: AsyncClient) -> None:
    """GET /health returns 200 OK with database connection status."""
    response = await test_client.get("/health")
    assert response.status_code in (200, 503)
    body = response.json()
    assert "status" in body
    assert "database" in body
    assert "pool" in body
