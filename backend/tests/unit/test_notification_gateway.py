"""
Unit tests for NotificationGateway: Slack and Discord webhook formatting and resilience.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.models.approval import Approval, ApprovalStatus
from app.infrastructure.notifications.notification_gateway import NotificationGateway


@pytest.fixture
def mock_http_client() -> AsyncMock:
    client = AsyncMock()
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    client.post.return_value = mock_resp
    return client


async def test_send_approval_request_alert_slack_and_discord(mock_http_client: AsyncMock) -> None:
    """Dispatches formatted payloads to both Slack and Discord webhooks."""
    gateway = NotificationGateway(
        slack_webhook_url="https://hooks.slack.com/services/test",
        discord_webhook_url="https://discord.com/api/webhooks/test",
        dashboard_base_url="http://agentguard.io",
        http_client=mock_http_client,
    )

    approval = Approval(
        id=uuid4(),
        run_id=uuid4(),
        status=ApprovalStatus.PENDING,
        action_intent={"action": "FILE_WRITE", "target": "config/prod/app.yaml"},
        decision_trace={"risk_score": 65},
    )

    success = await gateway.send_approval_request_alert(
        approval=approval,
        repo="octocat/Hello-World",
        pr_number=42,
    )

    assert success is True
    assert mock_http_client.post.call_count == 2


async def test_send_approval_alert_fails_safe_on_network_error() -> None:
    """Notification failure must not raise an exception or crash."""
    failing_client = AsyncMock()
    failing_client.post.side_effect = Exception("Slack API timeout")

    gateway = NotificationGateway(
        slack_webhook_url="https://hooks.slack.com/services/fail",
        http_client=failing_client,
    )

    approval = Approval(
        id=uuid4(),
        run_id=uuid4(),
        status=ApprovalStatus.PENDING,
        action_intent={"action": "COMMAND_EXEC", "target": "reboot"},
    )

    # Must return False and not raise
    success = await gateway.send_approval_request_alert(approval, "owner/repo", 1)
    assert success is False
