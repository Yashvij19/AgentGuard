"""
Health check and diagnostic API router.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import QueuePool

from app.config import settings
from app.infrastructure.database.connection import engine, get_db_session

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Structured health check payload."""

    status: str = Field(..., description="'healthy' or 'unhealthy'")
    database: str = Field(..., description="'connected' or 'disconnected'")
    app_env: str = Field(..., description="Active deployment environment")
    version: str = Field(default="0.1.0", description="AgentGuard backend version")
    pool: dict[str, Any] = Field(default_factory=dict, description="Database connection pool statistics")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health & DB Connectivity",
    description="Validates application status and executes an active probe query against PostgreSQL.",
)
async def health_check(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JSONResponse:
    pool = engine.pool
    pool_stats: dict[str, Any] = {}
    if isinstance(pool, QueuePool):
        pool_stats = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }

    try:
        await session.execute(text("SELECT 1"))
        data = HealthResponse(
            status="healthy",
            database="connected",
            app_env=settings.app_env.value,
            version="0.1.0",
            pool=pool_stats,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=data.model_dump(),
        )
    except Exception as exc:
        data = HealthResponse(
            status="unhealthy",
            database="disconnected",
            app_env=settings.app_env.value,
            version="0.1.0",
            pool={**pool_stats, "error": str(exc)},
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=data.model_dump(),
        )
