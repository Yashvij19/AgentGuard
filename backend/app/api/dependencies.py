"""
FastAPI dependency injection providers.
Extracts scoped sessions, repositories, and services from the composition root.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.container import Container, container
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.policy_repository import PolicyRepository
from app.infrastructure.database.repositories.run_repository import RunRepository
from app.infrastructure.database.repositories.webhook_repository import WebhookRepository
from app.services.approval_service import ApprovalService
from app.services.run_coordinator import RunCoordinator
from app.services.webhook_service import WebhookService


def get_container() -> Container:
    """Return the global application DI container."""
    return container


ContainerDep = Annotated[Container, Depends(get_container)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_run_repository(
    session: DbSessionDep,
    cont: ContainerDep,
) -> RunRepository:
    """FastAPI dependency yielding a session-scoped RunRepository."""
    return cont.get_run_repository(session)


def get_webhook_repository(
    session: DbSessionDep,
    cont: ContainerDep,
) -> WebhookRepository:
    """FastAPI dependency yielding a session-scoped WebhookRepository."""
    return cont.get_webhook_repository(session)


def get_event_repository(
    session: DbSessionDep,
    cont: ContainerDep,
) -> EventRepository:
    """FastAPI dependency yielding a session-scoped EventRepository."""
    return cont.get_event_repository(session)


def get_run_coordinator(
    session: DbSessionDep,
    cont: ContainerDep,
) -> RunCoordinator:
    """FastAPI dependency yielding a session-scoped RunCoordinator."""
    return cont.get_run_coordinator(session)


def get_webhook_service(
    session: DbSessionDep,
    cont: ContainerDep,
) -> WebhookService:
    """FastAPI dependency yielding a session-scoped WebhookService."""
    return cont.get_webhook_service(session)


def get_policy_repository(
    session: DbSessionDep,
    cont: ContainerDep,
) -> PolicyRepository:
    """FastAPI dependency yielding a session-scoped PolicyRepository."""
    return cont.get_policy_repository(session)

def get_approval_service(
    session: DbSessionDep,
    cont: ContainerDep,
) -> ApprovalService:
    """FastAPI dependency yielding a session-scoped ApprovalService."""
    return cont.get_approval_service(session)
