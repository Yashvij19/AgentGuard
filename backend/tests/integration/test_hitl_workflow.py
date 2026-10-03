"""
Integration test for Phase 4 Human-in-the-Loop (HITL) Governed Workflow:
Simulates end-to-end Pause -> Notification Alert -> Human Approval -> Tool Execution -> Resumption,
as well as the Human Rejection halt branch.
"""

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.agent.workflow import create_phase4_graph
from app.domain.models.action_intent import ActionType
from app.domain.models.approval import ApprovalStatus
from app.domain.models.llm_config import LLMProviderName, LLMResponse
from app.domain.models.policy_decision import Decision, PolicyDecision
from app.domain.models.run import RunStatus
from app.domain.protocols.github_client import GitHubClient
from app.domain.protocols.sandbox_runner import SandboxResult, SandboxRunner
from app.domain.protocols.tool_executor import ExecutionResult
from app.infrastructure.database.repositories.approval_repository import ApprovalRepository
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.run_repository import RunRepository
from app.infrastructure.notifications.notification_gateway import NotificationGateway
from app.services.approval_service import ApprovalService
from app.services.llm_gateway import LLMGateway
from app.services.policy_gateway import PolicyGateway
from app.services.run_coordinator import RunCoordinator
from app.services.tool_gateway import ToolGateway
from tests.factories import create_test_approval, create_test_run


@pytest.fixture
def mock_github() -> AsyncMock:
    client = AsyncMock(spec=GitHubClient)
    client.get_pr_diff = AsyncMock(
        return_value="--- a/config/prod/app.yaml\n+++ b/config/prod/app.yaml\n@@ -1 +1 @@\n-debug: false\n+debug: true\n"
    )
    client.get_pr_files = AsyncMock(return_value=["config/prod/app.yaml"])
    client.get_file_content = AsyncMock(return_value="debug: false\n")
    client.post_comment = AsyncMock(return_value=101)
    client.get_latest_pr_sha = AsyncMock(return_value="6dcb09b5b57875f334f61aebed695e2e4193db5e")
    return client


@pytest.fixture
def mock_sandbox() -> AsyncMock:
    runner = AsyncMock(spec=SandboxRunner)
    runner.run_command = AsyncMock(
        return_value=SandboxResult(
            exit_code=0,
            stdout="tests passed",
            stderr="",
            duration_ms=50,
            timed_out=False,
        )
    )
    return runner


@pytest.fixture
def mock_llm() -> AsyncMock:
    gw = AsyncMock(spec=LLMGateway)
    gw.generate = AsyncMock(
        return_value=LLMResponse(
            content="--- a/config/prod/app.yaml\n+++ b/config/prod/app.yaml\n@@ -1 +1 @@\n-debug: false\n+debug: true\n",
            model="gemini-2.0-flash",
            provider=LLMProviderName.GEMINI,
            prompt_tokens=100,
            completion_tokens=30,
            total_tokens=130,
            latency_ms=90,
            estimated_cost_usd=Decimal("0.0"),
        )
    )
    return gw


@pytest.mark.asyncio
async def test_full_hitl_pause_approve_resume_flow(
    mock_github: AsyncMock,
    mock_sandbox: AsyncMock,
    mock_llm: AsyncMock,
) -> None:
    """
    Complete lifecycle test:
    1. Agent runs -> Patch node proposes sensitive write to config/prod/app.yaml.
    2. Policy Gateway returns REQUIRE_APPROVAL.
    3. Run transitions to PAUSED, Approval record created, Slack alert fired.
    4. LangGraph halts cleanly and writes [PAUSED - AWAITING HUMAN APPROVAL] PR comment.
    5. Reviewer approves -> ToolGateway executes with is_approved=True.
    6. Coordinator resumes run -> transitions to RUNNING -> COMPLETED.
    """
    run = create_test_run(status=RunStatus.RUNNING)

    # In-memory repositories & mocks
    stored_runs = {run.id: run}
    stored_approvals = {}
    stored_events = []

    mock_run_repo = AsyncMock(spec=RunRepository)
    mock_run_repo.get_by_id = AsyncMock(side_effect=lambda rid: stored_runs.get(rid))

    async def _update_status(run_id, status, **kw):
        r = stored_runs[run_id].model_copy(update={"status": status, **kw})
        stored_runs[run_id] = r
        return r

    mock_run_repo.update_status = AsyncMock(side_effect=_update_status)

    mock_event_repo = AsyncMock(spec=EventRepository)

    async def _append_event(event):
        stored_events.append(event)
        return event

    mock_event_repo.append = AsyncMock(side_effect=_append_event)

    mock_approval_repo = AsyncMock(spec=ApprovalRepository)

    async def _create_approval(approval):
        stored_approvals[approval.id] = approval
        return approval

    mock_approval_repo.create = AsyncMock(side_effect=_create_approval)
    mock_approval_repo.get_by_id = AsyncMock(side_effect=lambda aid: stored_approvals.get(aid))

    async def _update_decision(approval_id, status, decided_by, rejection_reason=None):
        app = stored_approvals[approval_id].model_copy(
            update={
                "status": status,
                "decided_by": decided_by,
                "rejection_reason": rejection_reason,
            }
        )
        stored_approvals[approval_id] = app
        return app

    mock_approval_repo.update_decision = AsyncMock(side_effect=_update_decision)

    # Policy Gateway: Sensitive write requires approval
    mock_policy_gw = AsyncMock(spec=PolicyGateway)

    async def _evaluate_intent(intent, repo):
        if intent.action == ActionType.FILE_WRITE:
            return PolicyDecision(
                run_id=intent.run_id,
                action_intent_id=intent.id,
                decision=Decision.REQUIRE_APPROVAL,
                rule_matched="sensitive_paths",
                reason="Modification of production config requires operator authorization",
            )
        return PolicyDecision(
            run_id=intent.run_id,
            action_intent_id=intent.id,
            decision=Decision.ALLOW,
            rule_matched="safe_read",
            reason="Permitted operation",
        )

    mock_policy_gw.evaluate_intent = AsyncMock(side_effect=_evaluate_intent)

    # Tool Gateway & Notifications
    mock_tool_gw = AsyncMock(spec=ToolGateway)
    mock_tool_gw.execute = AsyncMock(
        return_value=ExecutionResult(success=True, output="Commit applied to branch")
    )

    mock_notif_gw = AsyncMock(spec=NotificationGateway)
    mock_notif_gw.send_approval_request_alert = AsyncMock(return_value=True)
    mock_notif_gw.send_approval_resolved_alert = AsyncMock(return_value=True)

    approval_service = ApprovalService(
        approval_repository=mock_approval_repo,
        run_repository=mock_run_repo,
        event_repository=mock_event_repo,
        tool_gateway=mock_tool_gw,
        notification_gateway=mock_notif_gw,
    )

    # 1. Compile Phase 4 Graph & Execute Agent Workflow
    app = create_phase4_graph(
        github_client=mock_github,
        policy_gateway=mock_policy_gw,
        tool_gateway=mock_tool_gw,
        llm_gateway=mock_llm,
        approval_service=approval_service,
    )

    initial_state = {
        "run_id": run.id,
        "repo": run.repo,
        "pr_number": run.pr_number,
        "head_sha": run.head_sha,
        "changed_files": [],
        "action_intents": [],
        "policy_decisions": [],
        "decision_traces": [],
        "halted": False,
        "halt_reason": None,
        "paused": False,
        "pending_approval_id": None,
        "pause_reason": None,
        "error": None,
    }

    final_state = await app.ainvoke(initial_state)

    # 2. Verify Execution Paused Safely
    assert final_state["paused"] is True
    assert final_state["halted"] is True
    assert final_state["pending_approval_id"] is not None
    assert "requires human approval" in final_state["pause_reason"]

    # Verify run transitioned to PAUSED
    paused_run = stored_runs[run.id]
    assert paused_run.status == RunStatus.PAUSED

    # Verify Approval record exists in PENDING status
    approval_id = UUID(final_state["pending_approval_id"])
    created_approval = stored_approvals[approval_id]
    assert created_approval.status == ApprovalStatus.PENDING

    # Verify notification dispatched
    mock_notif_gw.send_approval_request_alert.assert_called_once()

    def _extract_intent(call_obj: Any) -> Any:
        return call_obj.args[0] if call_obj.args else call_obj.kwargs["action_intent"]

    # Verify ToolGateway was NOT executed yet for the sensitive write
    executed_actions = [_extract_intent(c).action for c in mock_tool_gw.execute.call_args_list]
    assert ActionType.FILE_WRITE not in executed_actions

    # Verify PR comment was generated with PAUSED status
    assert "PAUSED (Awaiting Human Approval" in final_state["summary_report"]
    assert "Action Paused" in final_state["summary_report"]

    # 3. Reviewer Approves via ApprovalService
    decision_result = await approval_service.approve(
        approval_id=approval_id,
        decided_by="lead-security-eng",
    )
    assert decision_result.status == ApprovalStatus.APPROVED
    assert decision_result.action_executed is True

    # ToolGateway now executed the sensitive write under explicit human authorization
    file_write_calls = [
        c
        for c in mock_tool_gw.execute.call_args_list
        if _extract_intent(c).action == ActionType.FILE_WRITE
    ]
    assert len(file_write_calls) == 1
    assert file_write_calls[0].kwargs.get("is_approved") is True

    # 4. Coordinator Resumes Run
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = True
    mock_session.execute.return_value = mock_result

    coordinator = RunCoordinator(
        session=mock_session,
        run_repository=mock_run_repo,
        event_repository=mock_event_repo,
        github_client=mock_github,
    )

    resumed_run = await coordinator.resume_run(run.id, approval_id)
    assert resumed_run.status == RunStatus.COMPLETED

    # Verify complete event trail
    event_types = [e.event_type for e in stored_events]
    assert any(et.value == "approval_requested" for et in event_types)
    assert any(et.value == "approval_granted" for et in event_types)


@pytest.mark.asyncio
async def test_full_hitl_rejection_halts_cleanly(
    mock_github: AsyncMock,
    mock_sandbox: AsyncMock,
    mock_llm: AsyncMock,
) -> None:
    """
    Rejection lifecycle test:
    When reviewer rejects the pending action, status transitions to REJECTED,
    audit event is logged, and ToolGateway is NEVER executed.
    """
    run = create_test_run(status=RunStatus.PAUSED)
    stored_runs = {run.id: run}
    mock_run_repo = AsyncMock(spec=RunRepository)
    mock_run_repo.get_by_id = AsyncMock(side_effect=lambda rid: stored_runs.get(rid))
    mock_run_repo.update_status = AsyncMock()

    approval = create_test_approval(run_id=run.id, status=ApprovalStatus.PENDING)
    stored_approvals = {approval.id: approval}
    mock_approval_repo = AsyncMock(spec=ApprovalRepository)
    mock_approval_repo.get_by_id = AsyncMock(side_effect=lambda aid: stored_approvals.get(aid))

    async def _update_decision(approval_id, status, decided_by, rejection_reason=None):
        app = stored_approvals[approval_id].model_copy(
            update={
                "status": status,
                "decided_by": decided_by,
                "rejection_reason": rejection_reason,
            }
        )
        stored_approvals[approval_id] = app
        return app

    mock_approval_repo.update_decision = AsyncMock(side_effect=_update_decision)

    mock_event_repo = AsyncMock(spec=EventRepository)
    mock_event_repo.append = AsyncMock(side_effect=lambda e: e)

    mock_tool_gw = AsyncMock(spec=ToolGateway)
    mock_notif_gw = AsyncMock(spec=NotificationGateway)

    approval_service = ApprovalService(
        approval_repository=mock_approval_repo,
        run_repository=mock_run_repo,
        event_repository=mock_event_repo,
        tool_gateway=mock_tool_gw,
        notification_gateway=mock_notif_gw,
    )

    decision_result = await approval_service.reject(
        approval_id=approval.id,
        decided_by="secops-lead",
        reason="Dangerous file modification violates production change freeze",
    )

    assert decision_result.status == ApprovalStatus.REJECTED
    assert decision_result.action_executed is False

    # Guard: ToolGateway must NEVER execute on rejection
    mock_tool_gw.execute.assert_not_called()
