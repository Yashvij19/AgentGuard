"""
Integration tests for Action Ledger and Operational Stats REST API endpoints.
Tests the API routing, serialization, and aggregation contracts using mock repositories.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.dependencies import (
    get_approval_service,
    get_event_repository,
    get_policy_repository,
    get_provider_health_repository,
    get_run_repository,
)
from app.domain.models.policy_decision import Decision, PolicyDecision
from app.domain.models.provider_health import CircuitState, ProviderHealth
from app.domain.models.run import Run, RunStatus, TriggerType
from app.domain.models.run_event import EventType, RunEvent
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.policy_repository import PolicyRepository
from app.infrastructure.database.repositories.provider_health_repository import (
    ProviderHealthRepository,
)
from app.infrastructure.database.repositories.run_repository import RunRepository
from app.main import app
from app.services.approval_service import ApprovalService


@pytest.mark.asyncio
async def test_get_stats_empty_database(test_client: AsyncClient) -> None:
    """Verify /api/runs/stats behaves safely with zero runs in the database."""
    mock_run_repo = AsyncMock(spec=RunRepository)
    mock_run_repo.get_aggregate_stats.return_value = {
        "total_runs": 0,
        "completed_runs": 0,
        "failed_runs": 0,
        "paused_runs": 0,
        "success_rate_percent": 0.0,
        "total_cost_usd": Decimal("0.000000"),
        "avg_duration_seconds": 0.0,
    }
    mock_approval_service = AsyncMock(spec=ApprovalService)
    mock_approval_service.list_pending.return_value = []

    app.dependency_overrides[get_run_repository] = lambda: mock_run_repo
    app.dependency_overrides[get_approval_service] = lambda: mock_approval_service

    try:
        response = await test_client.get("/api/runs/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_runs"] == 0
        assert data["completed_runs"] == 0
        assert data["success_rate_percent"] == 0.0
        assert data["pending_approvals"] == 0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_stats_aggregated(test_client: AsyncClient) -> None:
    """Verify aggregate KPIs calculation across completed and failed runs."""
    mock_run_repo = AsyncMock(spec=RunRepository)
    mock_run_repo.get_aggregate_stats.return_value = {
        "total_runs": 2,
        "completed_runs": 1,
        "failed_runs": 1,
        "paused_runs": 0,
        "success_rate_percent": 50.0,
        "total_cost_usd": Decimal("0.070000"),
        "avg_duration_seconds": 15.2,
    }
    mock_approval_service = AsyncMock(spec=ApprovalService)
    mock_approval_service.list_pending.return_value = []

    app.dependency_overrides[get_run_repository] = lambda: mock_run_repo
    app.dependency_overrides[get_approval_service] = lambda: mock_approval_service

    try:
        response = await test_client.get("/api/runs/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_runs"] == 2
        assert data["completed_runs"] == 1
        assert data["failed_runs"] == 1
        assert data["success_rate_percent"] == 50.0
        assert Decimal(str(data["total_cost_usd"])) == Decimal("0.070000")
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_run_trace(test_client: AsyncClient) -> None:
    """Verify /api/runs/{id}/trace synthesizes policy decisions and audit events."""
    run_id = uuid4()
    mock_run = Run(
        id=run_id,
        repo="octocat/Hello-World",
        pr_number=10,
        head_sha="sha10",
        trigger_type=TriggerType.PULL_REQUEST,
        status=RunStatus.RUNNING,
    )
    decision = PolicyDecision(
        id=uuid4(),
        run_id=run_id,
        action_intent_id=uuid4(),
        decision=Decision.ALLOW,
        rule_matched="capabilities.allowed",
        risk_score=15,
        opa_query_id="opa-123",
        reason="Action allowed by policy",
        details={
            "step_name": "investigate",
            "action_type": "FILE_READ",
            "target": "src/main.py",
            "capability": "filesystem.read",
        },
    )
    event = RunEvent(
        id=uuid4(),
        run_id=run_id,
        step_name="investigate",
        event_type=EventType.POLICY_DECISION,
        content={"evidence_key": "evidence_val"},
        tokens_used=100,
        latency_ms=250,
    )

    mock_run_repo = AsyncMock(spec=RunRepository)
    mock_run_repo.get_by_id.return_value = mock_run
    mock_policy_repo = AsyncMock(spec=PolicyRepository)
    mock_policy_repo.get_decisions_for_run.return_value = [decision]
    mock_event_repo = AsyncMock(spec=EventRepository)
    mock_event_repo.get_events_for_run.return_value = [event]

    app.dependency_overrides[get_run_repository] = lambda: mock_run_repo
    app.dependency_overrides[get_policy_repository] = lambda: mock_policy_repo
    app.dependency_overrides[get_event_repository] = lambda: mock_event_repo

    try:
        response = await test_client.get(f"/api/runs/{run_id}/trace")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == str(run_id)
        assert len(data["traces"]) == 1
        trace = data["traces"][0]
        assert trace["step_name"] == "investigate"
        assert trace["decision"] == "ALLOW"
        assert trace["rule_matched"] == "capabilities.allowed"
        assert trace["risk_score"] == 15
        assert trace["evidence"] == {"evidence_key": "evidence_val"}
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_run_cost(test_client: AsyncClient) -> None:
    """Verify /api/runs/{id}/cost aggregates token breakdown per provider."""
    run_id = uuid4()
    mock_run = Run(
        id=run_id,
        repo="octocat/Hello-World",
        pr_number=11,
        head_sha="sha11",
        trigger_type=TriggerType.PULL_REQUEST,
        status=RunStatus.COMPLETED,
        total_tokens=1500,
        total_cost_usd=Decimal("0.035000"),
    )
    event = RunEvent(
        id=uuid4(),
        run_id=run_id,
        step_name="plan",
        event_type=EventType.LLM_CALL,
        content={
            "provider": "gemini",
            "model": "gemini-2.0-flash",
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "cost_usd": "0.035000",
        },
        tokens_used=1500,
        latency_ms=800,
    )

    mock_run_repo = AsyncMock(spec=RunRepository)
    mock_run_repo.get_by_id.return_value = mock_run
    mock_event_repo = AsyncMock(spec=EventRepository)
    mock_event_repo.get_events_for_run.return_value = [event]

    app.dependency_overrides[get_run_repository] = lambda: mock_run_repo
    app.dependency_overrides[get_event_repository] = lambda: mock_event_repo

    try:
        response = await test_client.get(f"/api/runs/{run_id}/cost")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == str(run_id)
        assert data["total_tokens"] == 1500
        assert len(data["providers"]) == 1
        provider_stat = data["providers"][0]
        assert provider_stat["provider"] == "gemini"
        assert provider_stat["model"] == "gemini-2.0-flash"
        assert provider_stat["input_tokens"] == 1000
        assert provider_stat["output_tokens"] == 500
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_providers_health(test_client: AsyncClient) -> None:
    """Verify /api/runs/providers/health returns active circuit breaker snapshots."""
    health = ProviderHealth(
        id=uuid4(),
        provider="groq",
        model="llama-3.3-70b",
        window_start=datetime.now(UTC),
        request_count=100,
        error_count=2,
        timeout_count=0,
        avg_latency_ms=180.5,
        circuit_state=CircuitState.CLOSED,
    )

    mock_health_repo = AsyncMock(spec=ProviderHealthRepository)
    mock_health_repo.get_all_latest.return_value = [health]

    app.dependency_overrides[get_provider_health_repository] = lambda: mock_health_repo

    try:
        response = await test_client.get("/api/runs/providers/health")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        groq_stat = next(p for p in data if p["provider"] == "groq")
        assert groq_stat["circuit_state"] == "closed"
        assert groq_stat["avg_latency_ms"] == 180.5
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_hourly_outcomes(test_client: AsyncClient) -> None:
    """Verify /api/runs/analytics/hourly retrieves dynamically aggregated outcome intervals."""
    mock_run_repo = AsyncMock(spec=RunRepository)
    mock_run_repo.get_hourly_outcomes.return_value = [
        {"time": "14:00", "completed": 3, "paused": 1, "failed": 0, "active": True},
        {"time": "16:00", "completed": 0, "paused": 0, "failed": 0, "active": False},
    ]

    app.dependency_overrides[get_run_repository] = lambda: mock_run_repo

    try:
        response = await test_client.get("/api/runs/analytics/hourly")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["time"] == "14:00"
        assert data[0]["completed"] == 3
        assert data[0]["paused"] == 1
        assert data[0]["active"] is True
    finally:
        app.dependency_overrides.clear()

