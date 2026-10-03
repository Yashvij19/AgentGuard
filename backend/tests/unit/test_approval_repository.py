"""
Unit tests for ApprovalRepository: persistence, lookups, pending queue listing,
reviewer decision transitions, and timeout expiration.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import ApprovalNotFoundError, InvalidApprovalStateError
from app.domain.models.approval import Approval, ApprovalStatus
from app.infrastructure.database.models import ApprovalORM
from app.infrastructure.database.repositories.approval_repository import ApprovalRepository
from tests.factories import create_test_approval


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session: AsyncMock) -> ApprovalRepository:
    return ApprovalRepository(mock_session)


def _make_orm_from_domain(approval: Approval) -> ApprovalORM:
    return ApprovalORM(
        id=approval.id,
        run_id=approval.run_id,
        event_id=approval.event_id,
        status=approval.status.value,
        action_intent=approval.action_intent,
        decision_trace=approval.decision_trace,
        requested_at=approval.requested_at,
        decided_at=approval.decided_at,
        decided_by=approval.decided_by,
        rejection_reason=approval.rejection_reason,
    )


@pytest.mark.asyncio
async def test_create_persists_approval(repo: ApprovalRepository, mock_session: AsyncMock) -> None:
    approval = create_test_approval()
    result = await repo.create(approval)

    assert result.id == approval.id
    assert result.status == ApprovalStatus.PENDING
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_id_found(repo: ApprovalRepository, mock_session: AsyncMock) -> None:
    approval = create_test_approval()
    orm = _make_orm_from_domain(approval)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = orm
    mock_session.execute.return_value = mock_result

    fetched = await repo.get_by_id(approval.id)
    assert fetched is not None
    assert fetched.id == approval.id
    assert fetched.status == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_get_by_id_not_found(repo: ApprovalRepository, mock_session: AsyncMock) -> None:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    fetched = await repo.get_by_id(uuid4())
    assert fetched is None


@pytest.mark.asyncio
async def test_get_by_run_id(repo: ApprovalRepository, mock_session: AsyncMock) -> None:
    run_id = uuid4()
    app1 = create_test_approval(run_id=run_id)
    app2 = create_test_approval(run_id=run_id)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        _make_orm_from_domain(app1),
        _make_orm_from_domain(app2),
    ]
    mock_session.execute.return_value = mock_result

    results = await repo.get_by_run_id(run_id)
    assert len(results) == 2
    assert results[0].run_id == run_id


@pytest.mark.asyncio
async def test_get_pending_for_run(repo: ApprovalRepository, mock_session: AsyncMock) -> None:
    run_id = uuid4()
    app = create_test_approval(run_id=run_id, status=ApprovalStatus.PENDING)

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = _make_orm_from_domain(app)
    mock_session.execute.return_value = mock_result

    pending = await repo.get_pending_for_run(run_id)
    assert pending is not None
    assert pending.status == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_list_pending_with_repo_filter(
    repo: ApprovalRepository, mock_session: AsyncMock
) -> None:
    app1 = create_test_approval(status=ApprovalStatus.PENDING)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [_make_orm_from_domain(app1)]
    mock_session.execute.return_value = mock_result

    results = await repo.list_pending(limit=10, offset=0, repo="octocat/Hello-World")
    assert len(results) == 1
    assert results[0].status == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_update_decision_to_approved(
    repo: ApprovalRepository, mock_session: AsyncMock
) -> None:
    approval = create_test_approval(status=ApprovalStatus.PENDING)
    orm = _make_orm_from_domain(approval)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = orm
    mock_session.execute.return_value = mock_result

    updated = await repo.update_decision(
        approval_id=approval.id,
        status=ApprovalStatus.APPROVED,
        decided_by="reviewer@corp.internal",
    )

    assert updated.status == ApprovalStatus.APPROVED
    assert updated.decided_by == "reviewer@corp.internal"
    assert updated.decided_at is not None
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_update_decision_not_found_raises(
    repo: ApprovalRepository, mock_session: AsyncMock
) -> None:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(ApprovalNotFoundError):
        await repo.update_decision(
            approval_id=uuid4(),
            status=ApprovalStatus.APPROVED,
            decided_by="reviewer",
        )


@pytest.mark.asyncio
async def test_update_decision_already_decided_raises(
    repo: ApprovalRepository, mock_session: AsyncMock
) -> None:
    approval = create_test_approval(status=ApprovalStatus.APPROVED)
    orm = _make_orm_from_domain(approval)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = orm
    mock_session.execute.return_value = mock_result

    with pytest.raises(InvalidApprovalStateError):
        await repo.update_decision(
            approval_id=approval.id,
            status=ApprovalStatus.REJECTED,
            decided_by="reviewer",
        )


@pytest.mark.asyncio
async def test_expire_stale_approvals(repo: ApprovalRepository, mock_session: AsyncMock) -> None:
    stale_app = create_test_approval(status=ApprovalStatus.PENDING)
    stale_orm = _make_orm_from_domain(stale_app)
    stale_orm.requested_at = datetime.now(UTC) - timedelta(seconds=2000)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [stale_orm]
    mock_session.execute.return_value = mock_result

    expired = await repo.expire_stale_approvals(timeout_seconds=1800)
    assert len(expired) == 1
    assert expired[0].status == ApprovalStatus.EXPIRED
    assert stale_orm.status == ApprovalStatus.EXPIRED.value
    mock_session.flush.assert_called_once()
