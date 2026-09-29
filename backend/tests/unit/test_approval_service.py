"""
Unit tests for ApprovalService: request_approval, approve, reject,
stale expiration, and ToolGateway action execution.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.approval import Approval, ApprovalStatus
from app.domain.models.policy_decision import Decision, PolicyDecision
from app.domain.models.run import RunStatus
from app.domain.models.run_event import EventType, RunEvent
from app.domain.protocols.tool_executor import ExecutionResult
from app.infrastructure.database.repositories.approval_repository import ApprovalRepository
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.run_repository import RunRepository
from app.services.approval_service import ApprovalService
from app.services.tool_gateway import ToolGateway
from tests.factories import create_test_run


@pytest.fixture
def mock_approval_repo() -> AsyncMock:
    repo = AsyncMock(spec=ApprovalRepository)
    repo.create = AsyncMock(side_effect=lambda a: a)
    repo.update_decision = AsyncMock()
    repo.expire_stale_approvals = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_run_repo() -> AsyncMock:
    repo = AsyncMock(spec=RunRepository)
    repo.get_by_id = AsyncMock(side_effect=lambda run_id: create_test_run(run_id=run_id, status=RunStatus.RUNNING))
    repo.update_status = AsyncMock()
    return repo


@pytest.fixture
def mock_event_repo() -> AsyncMock:
    repo = AsyncMock(spec=EventRepository)
    repo.append = AsyncMock(side_effect=lambda e: e)
    return repo


@pytest.fixture
def mock_tool_gateway() -> AsyncMock:
    gw = AsyncMock(spec=ToolGateway)
    gw.execute = AsyncMock(return_value=ExecutionResult(success=True, output="Commit created"))
    return gw


@pytest.fixture
def approval_service(
    mock_approval_repo: AsyncMock,
    mock_run_repo: AsyncMock,
    mock_event_repo: AsyncMock,
    mock_tool_gateway: AsyncMock,
) -> ApprovalService:
    return ApprovalService(
        approval_repository=mock_approval_repo,
        run_repository=mock_run_repo,
        event_repository=mock_event_repo,
        tool_gateway=mock_tool_gateway,
    )


async def test_request_approval_pauses_run_and_creates_approval(
    approval_service: ApprovalService,
    mock_run_repo: AsyncMock,
    mock_event_repo: AsyncMock,
    mock_approval_repo: AsyncMock,
) -> None:
    """Requesting approval must pause the run, log an audit event, and persist PENDING approval."""
    run_id = uuid4()
    intent = ActionIntent(
        run_id=run_id,
        action=ActionType.FILE_WRITE,
        target="config/prod/app.yaml",
        operation="modify",
        capability="github.create_commit",
        reason="Deploy production configuration fix",
    )
    decision = PolicyDecision(
        run_id=run_id,
        action_intent_id=intent.id,
        decision=Decision.REQUIRE_APPROVAL,
        rule_matched="risk_requires_approval",
        risk_score=65,
        reason="Risk score 65 requires human approval",
    )

    approval = await approval_service.request_approval(run_id, intent, decision)

    # 1. Run paused
    mock_run_repo.update_status.assert_awaited_once_with(run_id=run_id, status=RunStatus.PAUSED)

    # 2. Audit event logged
    mock_event_repo.append.assert_awaited_once()
    event_arg: RunEvent = mock_event_repo.append.call_args[0][0]
    assert event_arg.event_type == EventType.APPROVAL_REQUESTED

    # 3. Approval created with status PENDING
    mock_approval_repo.create.assert_awaited_once()
    assert approval.status == ApprovalStatus.PENDING
    assert approval.action_intent["target"] == "config/prod/app.yaml"


async def test_approve_resumes_run_and_executes_action(
    approval_service: ApprovalService,
    mock_approval_repo: AsyncMock,
    mock_run_repo: AsyncMock,
    mock_event_repo: AsyncMock,
    mock_tool_gateway: AsyncMock,
) -> None:
    """Approving a request must resume run, log event, and dispatch through ToolGateway."""
    approval_id = uuid4()
    run_id = uuid4()
    intent = ActionIntent(
        run_id=run_id,
        action=ActionType.FILE_WRITE,
        target="src/main.py",
        operation="modify",
        capability="github.create_commit",
        reason="Apply patch to fix bug",
    )
    mock_approval = Approval(
        id=approval_id,
        run_id=run_id,
        status=ApprovalStatus.APPROVED,
        action_intent=intent.model_dump(mode="json"),
        decided_by="senior_dev",
    )
    mock_approval_repo.update_decision.return_value = mock_approval

    result = await approval_service.approve(approval_id, decided_by="senior_dev")

    # 1. Status updated
    mock_approval_repo.update_decision.assert_awaited_once_with(
        approval_id=approval_id,
        status=ApprovalStatus.APPROVED,
        decided_by="senior_dev",
    )

    # 2. Run resumed to RUNNING
    mock_run_repo.update_status.assert_awaited_once_with(run_id=run_id, status=RunStatus.RUNNING)

    # 3. Action executed via ToolGateway with is_approved=True
    mock_tool_gateway.execute.assert_awaited_once()
    _, call_kwargs = mock_tool_gateway.execute.call_args
    assert call_kwargs["is_approved"] is True
    assert result.action_executed is True
    assert result.status == ApprovalStatus.APPROVED


async def test_reject_records_rejection_and_does_not_execute(
    approval_service: ApprovalService,
    mock_approval_repo: AsyncMock,
    mock_event_repo: AsyncMock,
    mock_tool_gateway: AsyncMock,
) -> None:
    """Rejecting a request must update status, log event, and NOT execute tool."""
    approval_id = uuid4()
    run_id = uuid4()
    mock_approval = Approval(
        id=approval_id,
        run_id=run_id,
        status=ApprovalStatus.REJECTED,
        action_intent={"action": "file_write"},
        decided_by="security_officer",
        rejection_reason="Too risky for production",
    )
    mock_approval_repo.update_decision.return_value = mock_approval

    result = await approval_service.reject(
        approval_id=approval_id,
        decided_by="security_officer",
        reason="Too risky for production",
    )

    mock_approval_repo.update_decision.assert_awaited_once_with(
        approval_id=approval_id,
        status=ApprovalStatus.REJECTED,
        decided_by="security_officer",
        rejection_reason="Too risky for production",
    )

    mock_event_repo.append.assert_awaited_once()
    event_arg: RunEvent = mock_event_repo.append.call_args[0][0]
    assert event_arg.event_type == EventType.APPROVAL_REJECTED

    mock_tool_gateway.execute.assert_not_called()
    assert result.status == ApprovalStatus.REJECTED
    assert result.action_executed is False
