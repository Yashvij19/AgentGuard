"""
Approval Service.
Orchestrates the Human-in-the-Loop approval lifecycle: requesting approval,
pausing runs, executing approved actions, and handling rejections or expirations.
"""

from typing import Any
from uuid import UUID

import structlog

from app.domain.exceptions import RunNotFoundError
from app.domain.models.action_intent import ActionIntent
from app.domain.models.approval import Approval, ApprovalDecisionResult, ApprovalStatus
from app.domain.models.policy_decision import PolicyDecision
from app.domain.models.run import RunStatus
from app.domain.models.run_event import EventType, RunEvent
from app.infrastructure.database.repositories.approval_repository import ApprovalRepository
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.run_repository import RunRepository
from app.infrastructure.notifications.notification_gateway import NotificationGateway
from app.services.tool_gateway import ToolGateway

logger = structlog.get_logger(__name__)


class ApprovalService:
    """
    Coordinates human-in-the-loop approvals across database persistence,
    run state transitions, Action Ledger audit events, and ToolGateway execution.
    """

    def __init__(
        self,
        approval_repository: ApprovalRepository,
        run_repository: RunRepository,
        event_repository: EventRepository,
        tool_gateway: ToolGateway | None = None,
        notification_gateway: NotificationGateway | None = None,
    ) -> None:
        self._approval_repo = approval_repository
        self._run_repo = run_repository
        self._event_repo = event_repository
        self._tool_gateway = tool_gateway
        self._notification_gw = notification_gateway

    async def request_approval(
        self,
        run_id: UUID,
        action_intent: ActionIntent,
        decision: PolicyDecision,
    ) -> Approval:
        """
        Request human approval for an action requiring authorization.
        1. Verifies run exists.
        2. Transitions run to PAUSED.
        3. Appends EventType.APPROVAL_REQUESTED to Action Ledger.
        4. Creates and persists an Approval in PENDING status.
        """
        run = await self._run_repo.get_by_id(run_id)
        if not run:
            raise RunNotFoundError(f"Run '{run_id}' not found.")

        # Transition run to PAUSED
        await self._run_repo.update_status(run_id=run_id, status=RunStatus.PAUSED)

        # Log audit event in Action Ledger
        event = RunEvent(
            run_id=run_id,
            step_name="policy_gateway",
            event_type=EventType.APPROVAL_REQUESTED,
            content={
                "message": "Human approval required for action",
                "action_intent": action_intent.model_dump(mode="json"),
                "policy_decision": decision.model_dump(mode="json"),
            },
        )
        saved_event = await self._event_repo.append(event)

        # Create approval record
        approval = Approval(
            run_id=run_id,
            event_id=saved_event.id,
            status=ApprovalStatus.PENDING,
            action_intent=action_intent.model_dump(mode="json"),
            decision_trace=decision.model_dump(mode="json"),
        )
        created_approval = await self._approval_repo.create(approval)

        logger.info(
            "approval_requested",
            approval_id=str(created_approval.id),
            run_id=str(run_id),
            action=action_intent.action.value,
            target=action_intent.target,
        )
        if self._notification_gw:
            await self._notification_gw.send_approval_request_alert(
                approval=created_approval,
                repo=run.repo,
                pr_number=run.pr_number,
            )
        return created_approval

    async def approve(
        self,
        approval_id: UUID,
        decided_by: str,
        execute_action: bool = True,
    ) -> ApprovalDecisionResult:
        """
        Approve a pending action.
        1. Transitions approval to APPROVED.
        2. Logs EventType.APPROVAL_GRANTED to Action Ledger.
        3. Transitions run back to RUNNING.
        4. If execute_action and tool_gateway present, executes action with is_approved=True.
        """
        approval = await self._approval_repo.update_decision(
            approval_id=approval_id,
            status=ApprovalStatus.APPROVED,
            decided_by=decided_by,
        )

        run = await self._run_repo.get_by_id(approval.run_id)
        if not run:
            raise RunNotFoundError(f"Run '{approval.run_id}' not found.")

        # Log approval granted event
        await self._event_repo.append(
            RunEvent(
                run_id=approval.run_id,
                step_name="approval_service",
                event_type=EventType.APPROVAL_GRANTED,
                content={
                    "message": "Approval granted by operator",
                    "approval_id": str(approval_id),
                    "decided_by": decided_by,
                },
            )
        )

        # Transition run back to RUNNING
        await self._run_repo.update_status(run_id=approval.run_id, status=RunStatus.RUNNING)

        # Execute approved action via ToolGateway
        executed = False
        exec_result: dict[str, Any] | None = None

        if execute_action and self._tool_gateway:
            intent = ActionIntent.model_validate(approval.action_intent)
            result = await self._tool_gateway.execute(
                action_intent=intent,
                repo=run.repo,
                is_approved=True,
            )
            executed = result.success
            exec_result = result.model_dump(mode="json")

        logger.info(
            "approval_granted",
            approval_id=str(approval_id),
            run_id=str(approval.run_id),
            decided_by=decided_by,
            action_executed=executed,
        )
        if self._notification_gw:
            await self._notification_gw.send_approval_resolved_alert(
                approval=approval,
                repo=run.repo,
                pr_number=run.pr_number,
            )


        return ApprovalDecisionResult(
            approval_id=approval_id,
            run_id=approval.run_id,
            status=ApprovalStatus.APPROVED,
            decided_by=decided_by,
            action_executed=executed,
            execution_result=exec_result,
            message="Action approved and executed" if executed else "Action approved",
        )

    async def reject(
        self,
        approval_id: UUID,
        decided_by: str,
        reason: str | None = None,
    ) -> ApprovalDecisionResult:
        """
        Reject a pending action.
        1. Transitions approval to REJECTED with optional reason.
        2. Logs EventType.APPROVAL_REJECTED to Action Ledger.
        """
        approval = await self._approval_repo.update_decision(
            approval_id=approval_id,
            status=ApprovalStatus.REJECTED,
            decided_by=decided_by,
            rejection_reason=reason,
        )
        run = await self._run_repo.get_by_id(approval.run_id)
        if not run:
            raise RunNotFoundError(f"Run '{approval.run_id}' not found.")

        # Log rejection audit event
        await self._event_repo.append(
            RunEvent(
                run_id=approval.run_id,
                step_name="approval_service",
                event_type=EventType.APPROVAL_REJECTED,
                content={
                    "message": "Approval rejected by operator",
                    "approval_id": str(approval_id),
                    "decided_by": decided_by,
                    "reason": reason,
                },
            )
        )

        logger.info(
            "approval_rejected",
            approval_id=str(approval_id),
            run_id=str(approval.run_id),
            decided_by=decided_by,
            reason=reason,
        )
        if self._notification_gw:
            await self._notification_gw.send_approval_resolved_alert(
                approval=approval,
                repo=run.repo,
                pr_number=run.pr_number,
            )


        return ApprovalDecisionResult(
            approval_id=approval_id,
            run_id=approval.run_id,
            status=ApprovalStatus.REJECTED,
            decided_by=decided_by,
            action_executed=False,
            execution_result=None,
            message=f"Action rejected: {reason}" if reason else "Action rejected by operator",
        )

    async def expire_stale_approvals(self, timeout_seconds: int = 1800) -> list[Approval]:
        """
        Expire all pending approvals that have exceeded the timeout window.
        Logs EventType.APPROVAL_EXPIRED for each expired request and marks run as FAILED.
        """
        expired = await self._approval_repo.expire_stale_approvals(timeout_seconds=timeout_seconds)

        for item in expired:
            await self._event_repo.append(
                RunEvent(
                    run_id=item.run_id,
                    step_name="approval_service",
                    event_type=EventType.APPROVAL_EXPIRED,
                    content={
                        "message": f"Approval timed out after {timeout_seconds}s and expired",
                        "approval_id": str(item.id),
                    },
                )
            )
            # Mark the run as FAILED due to approval timeout
            await self._run_repo.update_status(run_id=item.run_id, status=RunStatus.FAILED)

        return expired

    async def get_approval(self, approval_id: UUID) -> Approval | None:
        """Fetch single approval detail by ID."""
        return await self._approval_repo.get_by_id(approval_id)

    async def list_pending(
        self,
        limit: int = 50,
        offset: int = 0,
        repo: str | None = None,
    ) -> list[Approval]:
        """List pending approvals ordered FIFO (oldest first)."""
        return await self._approval_repo.list_pending(limit=limit, offset=offset, repo=repo)

    async def get_approvals_for_run(self, run_id: UUID) -> list[Approval]:
        """Fetch all approvals for a specific run."""
        return await self._approval_repo.get_by_run_id(run_id)
