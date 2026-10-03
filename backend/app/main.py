"""
FastAPI application entrypoint for AgentGuard.
Initializes application lifecycle, middleware pipeline, error handlers, and route mounting.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health_router, runs_router, webhooks_router
from app.api.approvals.router import router as approvals_router
from app.api.logs.router import router as logs_router
from app.api.policies.router import router as policies_router

from app.config import settings
from app.container import container
from app.infrastructure.database.connection import Base, engine
import app.infrastructure.database.models  # noqa: F401 - Register ORM tables with Base.metadata
from app.infrastructure.observability.metrics import init_metrics
from app.infrastructure.observability.tracing import init_tracing, shutdown_tracing
from app.middleware import RequestIdMiddleware, register_error_handlers

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application startup and shutdown lifecycle.
    Verifies database connectivity, initializes telemetry, and disposes resources on termination.
    """
    logger.info(
        "agentguard_starting",
        app_env=settings.app_env.value,
        version="0.1.0",
    )

    # Initialize OpenTelemetry telemetry pipeline
    init_tracing(settings)
    init_metrics(settings)

    # Verify database connectivity and initialize schema
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database_connection_and_schema_ready")
    except Exception as exc:
        logger.critical(
            "database_initialization_failed",
            error=str(exc),
            note="AgentGuard strictly requires an active PostgreSQL instance (local Docker or Neon Postgres). Shutting down gracefully.",
        )
        shutdown_tracing()
        await container.aclose()
        raise RuntimeError(
            f"Database connection failed: {exc}. Please verify PostgreSQL is running and DATABASE_URL is valid."
        ) from exc

    yield

    logger.info("agentguard_shutting_down")
    shutdown_tracing()
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

    configured_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=configured_origins if "*" not in configured_origins else ["*"],
        allow_origin_regex=r"^https:\/\/.*\.vercel\.app$" if "*" not in configured_origins else None,
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
    application.include_router(webhooks_router, prefix="/api")
    application.include_router(runs_router)
    application.include_router(policies_router, prefix="/api/policies", tags=["policies"])
    application.include_router(approvals_router)
    application.include_router(logs_router)

    return application



app = create_app()
