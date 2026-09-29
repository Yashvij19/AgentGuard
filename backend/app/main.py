"""
FastAPI application entrypoint for AgentGuard.
Initializes application lifecycle, middleware pipeline, error handlers, and route mounting.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import health_router, runs_router, webhooks_router
from app.api.approvals.router import router as approvals_router
from app.api.policies.router import router as policies_router
from app.config import settings
from app.container import container
from app.middleware import RequestIdMiddleware, register_error_handlers

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application startup and shutdown lifecycle.
    Verifies database connectivity on boot and disposes resources on termination.
    """
    logger.info(
        "agentguard_starting",
        app_env=settings.app_env.value,
        version="0.1.0",
    )

    # Verify database connectivity
    try:
        async with container.session_factory() as session:
            await session.execute(text("SELECT 1"))
        logger.info("database_connection_healthy")
    except Exception as exc:
        logger.warning(
            "database_initial_connection_failed",
            error=str(exc),
            note="Will retry per request; check DATABASE_URL and network availability.",
        )

    yield

    logger.info("agentguard_shutting_down")
    await container.aclose()
    logger.info("agentguard_shutdown_complete")


def create_app() -> FastAPI:
    """
    Construct and configure the FastAPI application instance.
    """
    application = FastAPI(
        title="AgentGuard Backend",
        description="Governance and execution-control layer for autonomous coding agents.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
    )

    # CORS configuration
    allow_origins = ["*"] if settings.app_env == "development" else []
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Correlation ID tracking middleware
    application.add_middleware(RequestIdMiddleware)

    # Global domain exception handlers
    register_error_handlers(application)

    # Mount API routers
    application.include_router(health_router)
    application.include_router(webhooks_router)
    application.include_router(runs_router)
    application.include_router(policies_router, prefix="/api/policies", tags=["policies"])
    application.include_router(approvals_router)


    return application


app = create_app()
