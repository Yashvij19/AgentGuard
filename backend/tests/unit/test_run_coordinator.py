"""
Unit tests for RunCoordinator: advisory locking, commit-SHA staleness detection,
execution lifecycle transitions, and audit event recording.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.exceptions import ConcurrentRunError, StaleRunError
from app.domain.models.run import RunStatus, TriggerType
from app.domain.models.run_event import EventType
from app.domain.protocols.github_client import GitHubClient
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.run_repository import RunRepository
from app.services.run_coordinator import RunCoordinator
from tests.factories import create_test_run


@pytest.fixture
def mock_run_repo() -> AsyncMock:
    repo = AsyncMock(spec=RunRepository)
    repo.create = AsyncMock(side_effect=lambda r: r)
    repo.update_status = AsyncMock(side_effect=lambda run_id, status, **kw: create_test_run(run_id=run_id, status=status))
    repo.mark_stale = AsyncMock(side_effect=lambda run_id: create_test_run(run_id=run_id, status=RunStatus.STALE))
    repo.get_by_id = AsyncMock(side_effect=lambda run_id: create_test_run(run_id=run_id, status=RunStatus.QUEUED))
    return repo


@pytest.fixture
def mock_event_repo() -> AsyncMock:
    repo = AsyncMock(spec=EventRepository)
    repo.append = AsyncMock(side_effect=lambda e: e)
    return repo


def test_generate_lock_key_is_deterministic() -> None:
    """The advisory lock key must be deterministic, case-insensitive, and a 64-bit signed int."""
    key1 = RunCoordinator.generate_lock_key("octocat/Hello-World", 42)
    key2 = RunCoordinator.generate_lock_key("OCTOCAT/hello-world ", 42)
    key3 = RunCoordinator.generate_lock_key("octocat/Hello-World", 43)

    # Determinism & case normalization
    assert key1 == key2
    assert key1 != key3

    # Must fit in PostgreSQL 64-bit signed bigint
    assert -(2**63) <= key1 < 2**63


@pytest.mark.asyncio
async def test_lock_acquisition_failure_raises_concurrent_error(
    mock_run_repo: AsyncMock,
    mock_event_repo: AsyncMock,
    mock_github_client: GitHubClient,
) -> None:
    """When pg_try_advisory_xact_lock returns False, ConcurrentRunError must be raised."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = False
    mock_session.execute.return_value = mock_result

    target_run = create_test_run(pr_number=42)
    mock_run_repo.get_by_id.return_value = target_run

    coordinator = RunCoordinator(
        session=mock_session,
        run_repository=mock_run_repo,
        event_repository=mock_event_repo,
        github_client=mock_github_client,
    )

    with pytest.raises(ConcurrentRunError, match="currently locked by another active run"):
        await coordinator.execute_run(target_run.id)

    mock_run_repo.update_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_commit_staleness_marks_run_stale(
    mock_session: AsyncMock,
    mock_run_repo: AsyncMock,
    mock_event_repo: AsyncMock,
    mock_github_client: GitHubClient,
) -> None:
    """If PR head commit SHA has changed, run must be marked STALE and raise StaleRunError."""
    target_run = create_test_run(
        pr_number=42,
        head_sha="old_sha_111111111111111111111111111111111111",
    )
    mock_run_repo.get_by_id.return_value = target_run

    # GitHub reports newer commit
    mock_github_client.get_latest_pr_sha = AsyncMock(  # type: ignore[method-assign]
        return_value="newer_sha_999999999999999999999999999999999999"
    )

    coordinator = RunCoordinator(
        session=mock_session,
        run_repository=mock_run_repo,
        event_repository=mock_event_repo,
        github_client=mock_github_client,
    )

    with pytest.raises(StaleRunError, match="is stale"):
        await coordinator.execute_run(target_run.id)

    # Run should be marked STALE
    assert mock_run_repo.mark_stale.await_count == 1
    mock_run_repo.mark_stale.assert_awaited_once_with(target_run.id)

    # Staleness audit event should be logged
    assert mock_event_repo.append.await_count == 1
    event_arg = mock_event_repo.append.await_args[0][0]
    assert event_arg.event_type == EventType.DECISION
    assert "Run marked stale" in event_arg.content.get("message", "")


@pytest.mark.asyncio
async def test_successful_run_lifecycle_execution(
    mock_session: AsyncMock,
    mock_run_repo: AsyncMock,
    mock_event_repo: AsyncMock,
    mock_github_client: GitHubClient,
) -> None:
    """A normal run transitions QUEUED -> RUNNING -> COMPLETED and executes runner."""
    target_sha = "6dcb09b5b57875f334f61aebed695e2e4193db5e"
    mock_github_client.get_latest_pr_sha = AsyncMock(return_value=target_sha)  # type: ignore[method-assign]

    agent_runner = AsyncMock()

    coordinator = RunCoordinator(
        session=mock_session,
        run_repository=mock_run_repo,
        event_repository=mock_event_repo,
        github_client=mock_github_client,
        agent_runner=agent_runner,
    )

    # 1. Create run
    created = await coordinator.create_run(
        repo="octocat/Hello-World",
        pr_number=42,
        head_sha=target_sha,
        trigger_type=TriggerType.PULL_REQUEST,
    )
    mock_run_repo.create.assert_awaited_once()
    mock_run_repo.get_by_id.return_value = created

    # 2. Execute run
    await coordinator.execute_run(created.id)

    # Status transitioned to RUNNING then COMPLETED
    assert mock_run_repo.update_status.await_count == 2
    first_update = mock_run_repo.update_status.await_args_list[0]
    second_update = mock_run_repo.update_status.await_args_list[1]
    assert first_update.kwargs["status"] == RunStatus.RUNNING
    assert second_update.kwargs["status"] == RunStatus.COMPLETED

    # Agent runner invoked with run
    agent_runner.assert_awaited_once()

    # Initial coordinator queuing event recorded
    assert mock_event_repo.append.await_count == 1


@pytest.mark.asyncio
async def test_runner_failure_transitions_to_failed(
    mock_session: AsyncMock,
    mock_run_repo: AsyncMock,
    mock_event_repo: AsyncMock,
    mock_github_client: GitHubClient,
) -> None:
    """When agent runner fails, run must transition to FAILED and record error event."""
    target_sha = "6dcb09b5b57875f334f61aebed695e2e4193db5e"
    mock_github_client.get_latest_pr_sha = AsyncMock(return_value=target_sha)  # type: ignore[method-assign]

    agent_runner = AsyncMock(side_effect=RuntimeError("GitHub API rate limit exceeded"))

    coordinator = RunCoordinator(
        session=mock_session,
        run_repository=mock_run_repo,
        event_repository=mock_event_repo,
        github_client=mock_github_client,
        agent_runner=agent_runner,
    )

    target_run = create_test_run(pr_number=42, head_sha=target_sha)
    mock_run_repo.get_by_id.return_value = target_run

    with pytest.raises(RuntimeError, match="GitHub API rate limit exceeded"):
        await coordinator.execute_run(target_run.id)

    # Status must be updated to FAILED
    last_update = mock_run_repo.update_status.await_args_list[-1]
    assert last_update.kwargs["status"] == RunStatus.FAILED

    # Error event must be recorded
    last_event = mock_event_repo.append.await_args_list[-1][0][0]
    assert last_event.step_name == "coordinator"
    assert "GitHub API rate limit exceeded" in str(last_event.content.get("error"))
