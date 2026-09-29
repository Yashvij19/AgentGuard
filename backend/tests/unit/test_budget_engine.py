"""
Unit tests for BudgetEngine: cumulative and preemptive token/cost limits,
and max LLM API invocation checks.
"""

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.models.policy_decision import Decision
from app.domain.models.run_event import EventType, RunEvent
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.run_repository import RunRepository
from app.services.budget_engine import BudgetEngine
from tests.factories import create_test_policy, create_test_run


@pytest.fixture
def mock_run_repo() -> AsyncMock:
    return AsyncMock(spec=RunRepository)


@pytest.fixture
def mock_event_repo() -> AsyncMock:
    return AsyncMock(spec=EventRepository)


@pytest.mark.asyncio
async def test_budget_within_bounds(mock_run_repo: AsyncMock) -> None:
    run = create_test_run()
    run.total_tokens = 500
    run.total_cost_usd = Decimal("0.05")
    mock_run_repo.get_by_id.return_value = run

    engine = BudgetEngine(mock_run_repo)
    policy = create_test_policy()

    assessment = await engine.evaluate(run.id, policy)
    assert assessment.decision == Decision.ALLOW
    assert "within" in assessment.reason


@pytest.mark.asyncio
async def test_budget_run_not_found(mock_run_repo: AsyncMock) -> None:
    mock_run_repo.get_by_id.return_value = None
    engine = BudgetEngine(mock_run_repo)
    policy = create_test_policy()

    assessment = await engine.evaluate(uuid4(), policy)
    assert assessment.decision == Decision.DENY
    assert "not found" in assessment.reason


@pytest.mark.asyncio
async def test_preemptive_token_exceeded(mock_run_repo: AsyncMock) -> None:
    run = create_test_run()
    run.total_tokens = 95_000
    mock_run_repo.get_by_id.return_value = run

    engine = BudgetEngine(mock_run_repo)
    policy = create_test_policy()  # default max_tokens_per_run: 100_000

    assessment = await engine.evaluate(run.id, policy, estimated_tokens=10_000)
    assert assessment.decision == Decision.DENY
    assert "exceed budget limit" in assessment.reason


@pytest.mark.asyncio
async def test_preemptive_cost_exceeded(mock_run_repo: AsyncMock) -> None:
    run = create_test_run()
    run.total_cost_usd = Decimal("4.50")
    mock_run_repo.get_by_id.return_value = run

    engine = BudgetEngine(mock_run_repo)
    policy = create_test_policy()  # default max_cost_usd_per_run: 5.00

    assessment = await engine.evaluate(run.id, policy, estimated_cost=1.00)
    assert assessment.decision == Decision.DENY
    assert "exceeds budget limit" in assessment.reason


@pytest.mark.asyncio
async def test_max_llm_calls_exceeded(
    mock_run_repo: AsyncMock, mock_event_repo: AsyncMock
) -> None:
    run = create_test_run()
    mock_run_repo.get_by_id.return_value = run

    # 15 LLM call events (policy default max is 10)
    events = [
        RunEvent(
            run_id=run.id,
            step_name="test",
            event_type=EventType.LLM_CALL,
            content={},
        )
        for _ in range(15)
    ]
    mock_event_repo.get_events_for_run = AsyncMock(return_value=events)
    mock_event_repo.get_by_run_id = AsyncMock(return_value=events)
    engine = BudgetEngine(mock_run_repo, mock_event_repo)
    policy = create_test_policy()

    assessment = await engine.evaluate(run.id, policy)
    assert assessment.decision == Decision.DENY
    assert "exceeding limit of 10" in assessment.reason
