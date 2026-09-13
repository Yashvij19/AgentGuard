"""
Database connection and session lifecycle management for AgentGuard.
Utilizes SQLAlchemy 2.0 async engine and asyncpg driver.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base declarative class for all SQLAlchemy ORM models.
    AsyncAttrs enables lazy-loading attributes in async context when necessary.
    """

    pass


def create_engine_instance() -> AsyncEngine:
    """
    Instantiate an async engine tailored for PostgreSQL/Neon Postgres.

    Key Production Settings:
    - pool_pre_ping=True: Tests connections prior to usage. Critical for Neon serverless
      where compute endpoints suspend after inactivity.
    - pool_size & max_overflow: Prevents connection exhaustion while supporting bursts.
    """
    connect_args: dict[str, Any] = {}

    # Handle SSL configuration if required by provider (e.g. Neon)
    if "sslmode=require" in settings.database_url:
        connect_args["ssl"] = "require"

    # Strip query parameters that asyncpg handles via connect_args to prevent connection errors
    clean_url = settings.database_url.split("?")[0]

    return create_async_engine(
        clean_url,
        echo=(settings.app_env == "development" and settings.log_level == "DEBUG"),
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args=connect_args,
    )


# Application-wide async database engine
engine: AsyncEngine = create_engine_instance()

# Session factory for creating scoped async sessions
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevents attribute reload errors after committing
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency and context provider yielding a scoped async database session.
    Automatically commits on successful block completion or rolls back on exception.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
