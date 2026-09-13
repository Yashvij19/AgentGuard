"""
Webhook service: verifies signatures, enforces delivery idempotency,
and dispatches events to the RunCoordinator.
"""

import json
from typing import Any

from app.domain.exceptions import WebhookValidationError
from app.domain.models.run import Run, TriggerType
from app.domain.models.webhook_delivery import WebhookDelivery
from app.infrastructure.database.repositories.webhook_repository import WebhookRepository
from app.infrastructure.github.schemas import GitHubWebhookPayload
from app.infrastructure.github.webhook_validator import GitHubWebhookValidator
from app.services.run_coordinator import RunCoordinator


class WebhookService:
    """
    Ingests and validates GitHub webhooks, ensuring strict idempotency and signature security.
    """

    ALLOWED_PR_ACTIONS = {"opened", "synchronize", "reopened"}

    def __init__(
        self,
        webhook_repository: WebhookRepository,
        run_coordinator: RunCoordinator,
        webhook_secret: str,
    ) -> None:
        self._webhook_repo = webhook_repository
        self._run_coordinator = run_coordinator
        self._webhook_secret = webhook_secret

    async def handle_github_webhook(
        self,
        payload_bytes: bytes,
        signature_header: str | None,
        delivery_id: str | None,
        event_type: str | None,
    ) -> Run | None:
        """
        Process an incoming GitHub webhook.

        1. Verifies HMAC-SHA256 signature against raw bytes.
        2. Records delivery ID for idempotency (raises DuplicateDeliveryError if seen).
        3. Parses payload into typed GitHubWebhookPayload.
        4. Dispatches pull_request actions to the RunCoordinator.
        """
        # 1. Cryptographic Signature Verification
        GitHubWebhookValidator.verify_signature(
            payload_bytes=payload_bytes,
            signature_header=signature_header,
            secret=self._webhook_secret,
        )

        if not delivery_id:
            raise WebhookValidationError("Missing 'X-GitHub-Delivery' header.")

        if not event_type:
            raise WebhookValidationError("Missing 'X-GitHub-Event' header.")

        # 2. Parse payload
        try:
            raw_json: dict[str, Any] = json.loads(payload_bytes.decode("utf-8"))
            payload = GitHubWebhookPayload.model_validate(raw_json)
        except Exception as err:
            raise WebhookValidationError(f"Invalid JSON webhook payload: {err}") from err

        # 3. Idempotency Check & Ledger Record
        delivery = WebhookDelivery(
            github_delivery_id=delivery_id,
            event_type=event_type,
            payload_summary={
                "action": payload.action,
                "repo": payload.repository.full_name if payload.repository else None,
                "pr_number": payload.pr_number,
            },
        )
        await self._webhook_repo.record_delivery(delivery)

        # 4. Event Filtering & Dispatch
        if event_type == "pull_request" and payload.repository is not None:
            if payload.action in self.ALLOWED_PR_ACTIONS:
                if payload.pr_number is None or payload.head_sha is None:
                    raise WebhookValidationError("PR event missing PR number or head SHA.")

                run = await self._run_coordinator.create_run(
                    repo=payload.repository.full_name,
                    pr_number=payload.pr_number,
                    head_sha=payload.head_sha,
                    trigger_type=TriggerType.PULL_REQUEST,
                )
                return run

        # Other events (e.g. check_suite, ping, closed PRs) safely acknowledged without run
        return None
