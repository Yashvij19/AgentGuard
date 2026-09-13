"""
Global error handling and exception mapping for AgentGuard FastAPI endpoints.
Translates domain exceptions into structured HTTP JSON responses.
"""

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    AgentGuardError,
    BudgetExceededError,
    ConcurrentRunError,
    DuplicateDeliveryError,
    PolicyViolationError,
    RunNotFoundError,
    StaleRunError,
    WebhookValidationError,
)

logger = structlog.get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers with the FastAPI application."""

    @app.exception_handler(DuplicateDeliveryError)
    async def duplicate_delivery_handler(
        request: Request, exc: DuplicateDeliveryError
    ) -> JSONResponse:
        """
        Duplicate webhook delivery ID.
        Returns HTTP 200 OK so GitHub does not enter exponential backoff retry.
        """
        return JSONResponse(
            status_code=200,
            content={
                "status": "ignored",
                "message": exc.message,
            },
        )

    @app.exception_handler(WebhookValidationError)
    async def webhook_validation_handler(
        request: Request, exc: WebhookValidationError
    ) -> JSONResponse:
        """Cryptographic signature failure or missing webhook delivery headers."""
        return JSONResponse(
            status_code=400,
            content={
                "error": "WebhookValidationError",
                "message": exc.message,
            },
        )

    @app.exception_handler(RunNotFoundError)
    async def run_not_found_handler(
        request: Request, exc: RunNotFoundError
    ) -> JSONResponse:
        """Requested run UUID does not exist."""
        return JSONResponse(
            status_code=404,
            content={
                "error": "RunNotFoundError",
                "message": exc.message,
            },
        )

    @app.exception_handler(ConcurrentRunError)
    async def concurrent_run_handler(
        request: Request, exc: ConcurrentRunError
    ) -> JSONResponse:
        """Active run currently holds the lock for this pull request."""
        return JSONResponse(
            status_code=409,
            content={
                "error": "ConcurrentRunError",
                "message": exc.message,
            },
        )

    @app.exception_handler(StaleRunError)
    async def stale_run_handler(
        request: Request, exc: StaleRunError
    ) -> JSONResponse:
        """PR commit head has superseded the run's target commit-SHA."""
        return JSONResponse(
            status_code=409,
            content={
                "error": "StaleRunError",
                "message": exc.message,
            },
        )

    @app.exception_handler(PolicyViolationError)
    async def policy_violation_handler(
        request: Request, exc: PolicyViolationError
    ) -> JSONResponse:
        """Action was denied by policy engine."""
        return JSONResponse(
            status_code=403,
            content={
                "error": "PolicyViolationError",
                "message": exc.message,
            },
        )

    @app.exception_handler(BudgetExceededError)
    async def budget_exceeded_handler(
        request: Request, exc: BudgetExceededError
    ) -> JSONResponse:
        """Run or action exceeded token/cost limits."""
        return JSONResponse(
            status_code=429,
            content={
                "error": "BudgetExceededError",
                "message": exc.message,
            },
        )

    @app.exception_handler(AgentGuardError)
    async def general_domain_error_handler(
        request: Request, exc: AgentGuardError
    ) -> JSONResponse:
        """Catch-all for domain errors."""
        logger.error("domain_error_occurred", error_type=exc.__class__.__name__, message=exc.message)
        return JSONResponse(
            status_code=500,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Safety net for unhandled system exceptions."""
        logger.exception("unhandled_server_exception", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected server error occurred.",
            },
        )
