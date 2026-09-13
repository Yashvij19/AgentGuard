"""
Composition root and dependency injection container for AgentGuard.
Wires settings, database engines, external clients, repositories, and services.
"""

from collections.abc import Awaitable, Callable
from typing import cast

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.agent.workflow import create_agent_runner
from app.config import Settings
from app.config import settings as app_settings
from app.domain.models.run import Run
from app.domain.protocols.github_client import GitHubClient
from app.infrastructure.database.connection import (
    async_session_factory as default_session_factory,
)
from app.infrastructure.database.connection import (
    engine as default_engine,
)
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.run_repository import RunRepository
from app.infrastructure.database.repositories.webhook_repository import WebhookRepository
from app.infrastructure.github.client import AsyncGitHubClient
from app.services.run_coordinator import RunCoordinator
from app.services.webhook_service import WebhookService


class Container:
    """
    Central dependency injection container managing application singletons
    and producing request-scoped services and repositories.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        engine: AsyncEngine | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        github_client: GitHubClient | None = None,
        agent_runner_factory: (
            Callable[[GitHubClient, EventRepository], Callable[[Run], Awaitable[None]]] | None
        ) = None,
    ) -> None:
        self.settings: Settings = settings or app_settings
        self.engine: AsyncEngine = engine or default_engine
        self.session_factory: async_sessionmaker[AsyncSession] = (
            session_factory or default_session_factory
        )
        self.github_client: GitHubClient = github_client or AsyncGitHubClient(
            app_id=self.settings.github_app_id,
            private_key=self.settings.github_private_key,
        )
        self._agent_runner_factory = agent_runner_factory or create_agent_runner

    def get_run_repository(self, session: AsyncSession) -> RunRepository:
        """Create a request-scoped RunRepository bound to the current session."""
        return RunRepository(session)

    def get_webhook_repository(self, session: AsyncSession) -> WebhookRepository:
        """Create a request-scoped WebhookRepository bound to the current session."""
        return WebhookRepository(session)

    def get_event_repository(self, session: AsyncSession) -> EventRepository:
        """Create a request-scoped EventRepository bound to the current session."""
        return EventRepository(session)

    def get_run_coordinator(self, session: AsyncSession) -> RunCoordinator:
        """
        Assemble a request-scoped RunCoordinator with injected repositories,
        GitHub client, and compiled LangGraph workflow runner.
        """
        run_repo = self.get_run_repository(session)
        event_repo = self.get_event_repository(session)
        runner = self._agent_runner_factory(self.github_client, event_repo)

        return RunCoordinator(
            session=session,
            run_repository=run_repo,
            event_repository=event_repo,
            github_client=self.github_client,
            agent_runner=runner,
        )

    def get_webhook_service(self, session: AsyncSession) -> WebhookService:
        """
        Assemble a request-scoped WebhookService injecting WebhookRepository,
        RunCoordinator, and configured webhook secret.
        """
        webhook_repo = self.get_webhook_repository(session)
        run_coordinator = self.get_run_coordinator(session)

        return WebhookService(
            webhook_repository=webhook_repo,
            run_coordinator=run_coordinator,
            webhook_secret=self.settings.github_webhook_secret,
        )

    async def aclose(self) -> None:
        """
        Gracefully dispose of database connection pools and external HTTP clients.
        Called during FastAPI application shutdown lifespan.
        """
        if hasattr(self.github_client, "aclose"):
            await cast(AsyncGitHubClient, self.github_client).aclose()
        await self.engine.dispose()


# Global application container instance
container = Container()
