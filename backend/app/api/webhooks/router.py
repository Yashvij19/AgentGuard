"""
GitHub webhook ingestion router.
"""

import asyncio
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request, status
from fastapi.responses import JSONResponse

from app.api.dependencies import DbSessionDep, get_webhook_service
from app.api.webhooks.schemas import WebhookResponse
from app.services.webhook_service import WebhookService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def _execute_run_in_background(run_id: UUID) -> None:
    """Execute the governed agent workflow for a queued run asynchronously."""
    try:
        from app.container import container
        async with container.session_factory() as session:
            coordinator = container.get_run_coordinator(session)
            # Ensure transaction visibility across async connection pools
            for _ in range(5):
                existing = await coordinator._run_repo.get_by_id(run_id)
                if existing:
                    break
                await asyncio.sleep(0.1)
            await coordinator.execute_run(run_id)
            await session.commit()
    except Exception as exc:
        logger.error("background_run_execution_failed", run_id=str(run_id), error=str(exc))


@router.post(
    "/github",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest GitHub Webhook",
    description="Validates cryptographic HMAC signature, verifies delivery idempotency, and dispatches PR runs.",
)
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: DbSessionDep,
    webhook_service: Annotated[WebhookService, Depends(get_webhook_service)],
    x_hub_signature_256: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
    x_github_delivery: Annotated[str | None, Header(alias="X-GitHub-Delivery")] = None,
    x_github_event: Annotated[str | None, Header(alias="X-GitHub-Event")] = None,
) -> JSONResponse:
    """
    Handle incoming GitHub webhook deliveries.
    Cryptographically verifies the HMAC-SHA256 signature and records delivery ID.
    """
    payload_bytes = await request.body()

    run = await webhook_service.handle_github_webhook(
        payload_bytes=payload_bytes,
        signature_header=x_hub_signature_256,
        delivery_id=x_github_delivery,
        event_type=x_github_event,
    )

    if run is not None:
        await session.commit()
        background_tasks.add_task(_execute_run_in_background, run.id)
        response_data = WebhookResponse(
            status="accepted",
            message=f"Run '{run.id}' initiated for PR #{run.pr_number}.",
            run_id=run.id,
            delivery_id=x_github_delivery,
        )
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=response_data.model_dump(mode="json"),
        )

    response_data = WebhookResponse(
        status="ignored",
        message=f"Webhook event '{x_github_event}' was safely received and recorded, but no agent run was required.",
        delivery_id=x_github_delivery,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response_data.model_dump(mode="json"),
    )
