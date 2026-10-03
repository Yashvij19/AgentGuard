"""
Test data factories for AgentGuard tests.
"""

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.domain.models.action_intent import ActionIntent, ActionType
from app.domain.models.approval import Approval, ApprovalStatus
from app.domain.models.policy import (
    BudgetConfig,
    CapabilityConfig,
    CommandConfig,
    FilesystemConfig,
    NetworkConfig,
    Policy,
    PolicyConfig,
    RiskThresholdConfig,
)
from app.domain.models.run import Run, RunStatus, TriggerType
from app.domain.models.run_event import EventType, RunEvent


def compute_webhook_signature(payload_bytes: bytes, secret: str) -> str:
    """Compute the HMAC-SHA256 signature header matching GitHub's format."""
    signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"


def create_test_run(
    run_id: UUID | None = None,
    repo: str = "octocat/Hello-World",
    pr_number: int = 42,
    head_sha: str = "6dcb09b5b57875f334f61aebed695e2e4193db5e",
    trigger_type: TriggerType = TriggerType.PULL_REQUEST,
    status: RunStatus = RunStatus.QUEUED,
    policy_version: int | None = 1,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> Run:
    """Factory helper generating a domain Run instance."""
    now = datetime.now(UTC)
    return Run(
        id=run_id or uuid4(),
        repo=repo,
        pr_number=pr_number,
        head_sha=head_sha,
        trigger_type=trigger_type,
        status=status,
        policy_version=policy_version,
        started_at=started_at,
        completed_at=completed_at,
        created_at=now,
        updated_at=now,
    )


def create_test_event(
    run_id: UUID | None = None,
    step_name: str = "plan",
    event_type: EventType = EventType.DECISION,
    content: dict[str, Any] | None = None,
    tokens_used: int = 150,
    latency_ms: int = 420,
) -> RunEvent:
    """Factory helper generating a domain RunEvent instance."""
    return RunEvent(
        id=uuid4(),
        run_id=run_id or uuid4(),
        step_name=step_name,
        event_type=event_type,
        content=content or {"note": "Test decision event"},
        tokens_used=tokens_used,
        latency_ms=latency_ms,
        created_at=datetime.now(UTC),
    )


def create_test_webhook_payload(
    action: str = "opened",
    repo_full_name: str = "octocat/Hello-World",
    pr_number: int = 42,
    head_sha: str = "6dcb09b5b57875f334f61aebed695e2e4193db5e",
) -> dict[str, Any]:
    """Factory helper generating a typed GitHub PR webhook payload dict."""
    return {
        "action": action,
        "number": pr_number,
        "pull_request": {
            "number": pr_number,
            "title": "Fix memory leak in buffer pool",
            "body": "Closes #101 by ensuring buffer cleanup.",
            "head": {
                "sha": head_sha,
                "ref": "fix/buffer-leak",
            },
            "base": {
                "sha": "1234567890abcdef1234567890abcdef12345678",
                "ref": "main",
            },
            "html_url": f"https://github.com/{repo_full_name}/pull/{pr_number}",
        },
        "repository": {
            "id": 1296269,
            "name": repo_full_name.split("/")[-1],
            "full_name": repo_full_name,
            "owner": {
                "login": repo_full_name.split("/")[0],
            },
        },
        "sender": {
            "login": "octocat",
        },
    }


def create_test_action_intent(
    run_id: UUID | None = None,
    action: ActionType = ActionType.FILE_READ,
    target: str = "src/main.py",
    operation: str = "read",
    capability: str = "github.read_file",
    reason: str = "Read source file to formulate fix",
    metadata: dict[str, Any] | None = None,
) -> ActionIntent:
    """Factory helper generating a domain ActionIntent instance."""
    return ActionIntent(
        id=uuid4(),
        run_id=run_id or uuid4(),
        action=action,
        target=target,
        operation=operation,
        capability=capability,
        reason=reason,
        metadata=metadata or {},
        created_at=datetime.now(UTC),
    )


def create_test_policy_config() -> PolicyConfig:
    """Factory helper generating a standard PolicyConfig."""
    return PolicyConfig(
        version=1,
        capabilities=CapabilityConfig(
            allow=["github.read_file", "github.read_pr", "github.comment_pr"],
            approval=["github.create_commit"],
            deny=["github.delete_repository"],
        ),
        filesystem=FilesystemConfig(
            read=["**/*"],
            write=["src/**/*", "tests/**/*"],
        ),
        commands=CommandConfig(
            allow=["^pytest.*"],
            deny=[".*rm -rf.*"],
        ),
        network=NetworkConfig(
            allowed_domains=["api.github.com"],
        ),
        risk_thresholds=RiskThresholdConfig(
            require_approval=50,
            deny=80,
        ),
        budget=BudgetConfig(
            max_tokens_per_run=100_000,
            max_cost_usd_per_run=5.00,
            max_llm_calls_per_run=10,
        ),
    )


def create_test_policy(repo: str = "octocat/Hello-World", version: int = 1) -> Policy:
    """Factory helper generating a domain Policy instance."""
    now = datetime.now(UTC)
    return Policy(
        id=uuid4(),
        repo=repo,
        yaml_content="# Test policy",
        parsed_content=create_test_policy_config(),
        version=version,
        created_at=now,
        updated_at=now,
    )


def create_test_approval(
    run_id: UUID | None = None,
    event_id: UUID | None = None,
    status: ApprovalStatus = ApprovalStatus.PENDING,
    action_intent: dict[str, Any] | None = None,
    decision_trace: dict[str, Any] | None = None,
    decided_by: str | None = None,
    rejection_reason: str | None = None,
) -> Approval:
    """Factory helper generating a domain Approval instance."""
    now = datetime.now(UTC)
    intent = action_intent or {
        "id": str(uuid4()),
        "run_id": str(run_id or uuid4()),
        "action": "file_write",
        "target": "config/prod/app.yaml",
        "operation": "modify",
        "capability": "github.create_commit",
        "reason": "Update production configuration",
        "metadata": {},
    }
    decision = decision_trace or {
        "run_id": str(run_id or uuid4()),
        "decision": "REQUIRE_APPROVAL",
        "rule_matched": "sensitive_files",
        "reason": "Production path requires authorization",
    }
    return Approval(
        id=uuid4(),
        run_id=run_id or uuid4(),
        event_id=event_id or uuid4(),
        status=status,
        action_intent=intent,
        decision_trace=decision,
        requested_at=now,
        decided_at=now if status != ApprovalStatus.PENDING else None,
        decided_by=decided_by,
        rejection_reason=rejection_reason,
    )
