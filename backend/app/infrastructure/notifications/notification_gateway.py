"""
Notification Gateway for dispatching Human-in-the-Loop alert cards
to Slack and Discord incoming webhooks.
"""

from typing import Any

import httpx
import structlog

from app.domain.models.approval import Approval, ApprovalStatus

logger = structlog.get_logger(__name__)


class NotificationGateway:
    """
    Sends structured alert messages to external team communication channels
    when actions require human approval or are resolved.
    """

    def __init__(
        self,
        slack_webhook_url: str | None = None,
        discord_webhook_url: str | None = None,
        dashboard_base_url: str = "http://localhost:3000",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._slack_url = slack_webhook_url
        self._discord_url = discord_webhook_url
        self._dashboard_url = dashboard_base_url.rstrip("/")
        self._client = http_client

    async def send_approval_request_alert(
        self,
        approval: Approval,
        repo: str,
        pr_number: int,
    ) -> bool:
        """
        Dispatch alert cards for a new pending approval.
        Fails safely: logs errors without raising exceptions to protect workflow integrity.
        """
        target = approval.action_intent.get("target", "unknown")
        action = approval.action_intent.get("action", "unknown")
        risk_score = approval.decision_trace.get("risk_score", 0)
        review_url = f"{self._dashboard_url}/approvals/{approval.id}"

        success = True

        if self._slack_url:
            slack_payload = {
                "text": f"🛡️ *AgentGuard Approval Required* on `{repo}#{pr_number}`",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🛡️ Agent Action Awaiting Approval",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Repository:*\n`{repo}#{pr_number}`"},
                            {"type": "mrkdwn", "text": f"*Risk Score:*\n`{risk_score}/100`"},
                            {"type": "mrkdwn", "text": f"*Action:*\n`{action}`"},
                            {"type": "mrkdwn", "text": f"*Target:*\n`{target}`"},
                        ],
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"👉 <{review_url}|*Review and Decide in Dashboard*>",
                        },
                    },
                ],
            }
            if not await self._dispatch_webhook(self._slack_url, slack_payload, "slack"):
                success = False

        if self._discord_url:
            discord_payload = {
                "content": f"🛡️ **AgentGuard Approval Required** on `{repo}#{pr_number}`",
                "embeds": [
                    {
                        "title": "Action Awaiting Human Review",
                        "url": review_url,
                        "color": 15105570,  # Orange
                        "fields": [
                            {
                                "name": "Repository",
                                "value": f"`{repo}#{pr_number}`",
                                "inline": True,
                            },
                            {"name": "Risk Score", "value": f"`{risk_score}/100`", "inline": True},
                            {"name": "Action", "value": f"`{action}`", "inline": True},
                            {"name": "Target", "value": f"`{target}`", "inline": False},
                        ],
                        "footer": {"text": f"Approval ID: {approval.id}"},
                    }
                ],
            }
            if not await self._dispatch_webhook(self._discord_url, discord_payload, "discord"):
                success = False

        return success

    async def send_approval_resolved_alert(
        self,
        approval: Approval,
        repo: str,
        pr_number: int,
    ) -> bool:
        """
        Dispatch update notification when an approval is resolved (approved or rejected).
        """
        status_label = (
            "✅ Approved" if approval.status == ApprovalStatus.APPROVED else "❌ Rejected"
        )
        color = 3066993 if approval.status == ApprovalStatus.APPROVED else 15158332  # Green vs Red

        success = True

        if self._slack_url:
            slack_payload = {
                "text": f"🛡️ Approval resolved on `{repo}#{pr_number}`: *{status_label}* by `{approval.decided_by}`",
            }
            if not await self._dispatch_webhook(self._slack_url, slack_payload, "slack"):
                success = False

        if self._discord_url:
            discord_payload = {
                "embeds": [
                    {
                        "title": f"Approval {status_label}",
                        "color": color,
                        "fields": [
                            {
                                "name": "Repository",
                                "value": f"`{repo}#{pr_number}`",
                                "inline": True,
                            },
                            {
                                "name": "Decided By",
                                "value": f"`{approval.decided_by}`",
                                "inline": True,
                            },
                        ],
                        "footer": {"text": f"Approval ID: {approval.id}"},
                    }
                ],
            }
            if not await self._dispatch_webhook(self._discord_url, discord_payload, "discord"):
                success = False

        return success

    async def _dispatch_webhook(self, url: str, payload: dict[str, Any], provider: str) -> bool:
        """Helper to post webhook JSON payload with error containment."""
        try:
            if self._client:
                resp = await self._client.post(url, json=payload, timeout=5.0)
                return resp.status_code in (200, 204)
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(url, json=payload)
                return resp.status_code in (200, 204)
        except Exception as exc:
            logger.warning(
                "notification_dispatch_failed",
                provider=provider,
                error=str(exc),
            )
            return False
