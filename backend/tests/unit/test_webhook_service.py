"""
Unit tests for WebhookService: signature validation, delivery idempotency,
event filtering, and run coordination dispatching.
"""

import json
from unittest.mock import AsyncMock

import pytest

from app.domain.exceptions import DuplicateDeliveryError, WebhookValidationError
from app.infrastructure.database.repositories.webhook_repository import WebhookRepository
from app.services.run_coordinator import RunCoordinator
from app.services.webhook_service import WebhookService
from tests.factories import (
    compute_webhook_signature,
    create_test_run,
    create_test_webhook_payload,
)

TEST_SECRET = "super-secret-webhook-key-12345"


@pytest.fixture
def mock_webhook_repo() -> AsyncMock:
    repo = AsyncMock(spec=WebhookRepository)
    repo.record_delivery = AsyncMock()
    return repo


@pytest.fixture
def mock_coordinator() -> AsyncMock:
    coord = AsyncMock(spec=RunCoordinator)
    coord.create_run = AsyncMock(return_value=create_test_run())
    return coord


@pytest.fixture
def webhook_service(
    mock_webhook_repo: AsyncMock,
    mock_coordinator: AsyncMock,
) -> WebhookService:
    return WebhookService(
        webhook_repository=mock_webhook_repo,
        run_coordinator=mock_coordinator,
        webhook_secret=TEST_SECRET,
    )


@pytest.mark.asyncio
async def test_valid_signature_and_pr_opened(
    webhook_service: WebhookService,
    mock_webhook_repo: AsyncMock,
    mock_coordinator: AsyncMock,
) -> None:
    """A valid PR opened webhook should be recorded and dispatched to the RunCoordinator."""
    payload_dict = create_test_webhook_payload(
        action="opened",
        repo_full_name="octocat/Hello-World",
        pr_number=42,
        head_sha="6dcb09b5b57875f334f61aebed695e2e4193db5e",
    )
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    signature = compute_webhook_signature(payload_bytes, TEST_SECRET)

    run = await webhook_service.handle_github_webhook(
        payload_bytes=payload_bytes,
        signature_header=signature,
        delivery_id="delivery-guid-1",
        event_type="pull_request",
    )

    assert run is not None
    assert mock_webhook_repo.record_delivery.await_count == 1
    delivery_arg = mock_webhook_repo.record_delivery.await_args[0][0]
    assert delivery_arg.github_delivery_id == "delivery-guid-1"
    assert delivery_arg.event_type == "pull_request"

    assert mock_coordinator.create_run.await_count == 1
    mock_coordinator.create_run.assert_awaited_once_with(
        repo="octocat/Hello-World",
        pr_number=42,
        head_sha="6dcb09b5b57875f334f61aebed695e2e4193db5e",
        trigger_type=mock_coordinator.create_run.await_args[1]["trigger_type"],
    )


@pytest.mark.asyncio
async def test_invalid_signature_raises_validation_error(
    webhook_service: WebhookService,
    mock_webhook_repo: AsyncMock,
    mock_coordinator: AsyncMock,
) -> None:
    """An invalid HMAC signature must raise WebhookValidationError and halt processing."""
    payload_bytes = b'{"action": "opened"}'
    invalid_signature = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

    with pytest.raises(WebhookValidationError, match="signature verification failed"):
        await webhook_service.handle_github_webhook(
            payload_bytes=payload_bytes,
            signature_header=invalid_signature,
            delivery_id="delivery-guid-2",
            event_type="pull_request",
        )

    mock_webhook_repo.record_delivery.assert_not_awaited()
    mock_coordinator.create_run.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_signature_header_raises_validation_error(
    webhook_service: WebhookService,
) -> None:
    """Missing signature header must be rejected immediately."""
    with pytest.raises(WebhookValidationError, match="Missing 'X-Hub-Signature-256' header"):
        await webhook_service.handle_github_webhook(
            payload_bytes=b"{}",
            signature_header=None,
            delivery_id="delivery-guid-3",
            event_type="pull_request",
        )


@pytest.mark.asyncio
async def test_missing_delivery_id_header_raises_validation_error(
    webhook_service: WebhookService,
) -> None:
    """Missing delivery ID header must raise WebhookValidationError."""
    payload_bytes = b"{}"
    signature = compute_webhook_signature(payload_bytes, TEST_SECRET)

    with pytest.raises(WebhookValidationError, match="Missing 'X-GitHub-Delivery' header"):
        await webhook_service.handle_github_webhook(
            payload_bytes=payload_bytes,
            signature_header=signature,
            delivery_id=None,
            event_type="pull_request",
        )


@pytest.mark.asyncio
async def test_missing_event_type_header_raises_validation_error(
    webhook_service: WebhookService,
) -> None:
    """Missing event type header must raise WebhookValidationError."""
    payload_bytes = b"{}"
    signature = compute_webhook_signature(payload_bytes, TEST_SECRET)

    with pytest.raises(WebhookValidationError, match="Missing 'X-GitHub-Event' header"):
        await webhook_service.handle_github_webhook(
            payload_bytes=payload_bytes,
            signature_header=signature,
            delivery_id="delivery-guid-4",
            event_type=None,
        )


@pytest.mark.asyncio
async def test_duplicate_delivery_raises_duplicate_error(
    webhook_service: WebhookService,
    mock_webhook_repo: AsyncMock,
    mock_coordinator: AsyncMock,
) -> None:
    """Duplicate delivery ID reported by repository must raise DuplicateDeliveryError."""
    payload_bytes = b"{}"
    signature = compute_webhook_signature(payload_bytes, TEST_SECRET)

    mock_webhook_repo.record_delivery.side_effect = DuplicateDeliveryError(
        "Webhook delivery 'delivery-dup' has already been processed."
    )

    with pytest.raises(DuplicateDeliveryError):
        await webhook_service.handle_github_webhook(
            payload_bytes=payload_bytes,
            signature_header=signature,
            delivery_id="delivery-dup",
            event_type="pull_request",
        )

    mock_coordinator.create_run.assert_not_awaited()


@pytest.mark.asyncio
async def test_ignored_event_type_returns_none(
    webhook_service: WebhookService,
    mock_webhook_repo: AsyncMock,
    mock_coordinator: AsyncMock,
) -> None:
    """Non-pull_request events (e.g. ping) should be recorded for audit but not dispatched."""
    payload_bytes = b'{"zen": "Keep it logically awesome."}'
    signature = compute_webhook_signature(payload_bytes, TEST_SECRET)

    run = await webhook_service.handle_github_webhook(
        payload_bytes=payload_bytes,
        signature_header=signature,
        delivery_id="delivery-ping",
        event_type="ping",
    )

    assert run is None
    assert mock_webhook_repo.record_delivery.await_count == 1
    mock_coordinator.create_run.assert_not_awaited()


@pytest.mark.asyncio
async def test_ignored_pr_action_returns_none(
    webhook_service: WebhookService,
    mock_webhook_repo: AsyncMock,
    mock_coordinator: AsyncMock,
) -> None:
    """Ignored PR actions (e.g. 'closed', 'labeled') should record delivery but not trigger run."""
    payload_dict = create_test_webhook_payload(action="closed")
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    signature = compute_webhook_signature(payload_bytes, TEST_SECRET)

    run = await webhook_service.handle_github_webhook(
        payload_bytes=payload_bytes,
        signature_header=signature,
        delivery_id="delivery-closed",
        event_type="pull_request",
    )

    assert run is None
    assert mock_webhook_repo.record_delivery.await_count == 1
    mock_coordinator.create_run.assert_not_awaited()
