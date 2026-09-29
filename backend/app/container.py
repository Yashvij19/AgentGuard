"""
Composition root and dependency injection container for AgentGuard.
Wires settings, database engines, external clients, repositories, and services.
"""

from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.agent.workflow import create_agent_runner
from app.config import Settings
from app.config import settings as app_settings
from app.domain.models.llm_config import (
    LLMGatewayConfig,
    LLMProviderConfig,
    LLMProviderName,
    RoutingStrategy,
    TaskType,
)
from app.domain.protocols.github_client import GitHubClient
from app.domain.protocols.policy_evaluator import PolicyEvaluator
from app.domain.protocols.sandbox_runner import SandboxRunner
from app.infrastructure.database.connection import (
    async_session_factory as default_session_factory,
)
from app.infrastructure.database.connection import (
    engine as default_engine,
)
from app.infrastructure.database.repositories.approval_repository import ApprovalRepository
from app.infrastructure.database.repositories.event_repository import EventRepository
from app.infrastructure.database.repositories.policy_repository import PolicyRepository
from app.infrastructure.database.repositories.run_repository import RunRepository
from app.infrastructure.database.repositories.webhook_repository import WebhookRepository
from app.infrastructure.github.client import AsyncGitHubClient
from app.infrastructure.llm.output_validator import OutputValidator
from app.infrastructure.llm.providers.gemini_provider import GeminiProvider
from app.infrastructure.llm.providers.groq_provider import GroqProvider
from app.infrastructure.llm.providers.nvidia_nim_provider import NVIDIANIMProvider
from app.infrastructure.notifications import NotificationGateway
from app.infrastructure.policy.opa_client import OPAClient
from app.infrastructure.policy.opa_evaluator import OPAEvaluator
from app.infrastructure.policy.rego_compiler import RegoCompiler
from app.infrastructure.sandbox import create_sandbox_runner
from app.services.approval_service import ApprovalService
from app.services.budget_engine import BudgetEngine
from app.services.llm_gateway import LLMGateway
from app.services.policy_gateway import PolicyGateway
from app.services.provider_registry import ProviderRegistry
from app.services.risk_engine import RiskEngine
from app.services.run_coordinator import RunCoordinator
from app.services.tool_gateway import ToolGateway
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
        sandbox_runner: SandboxRunner | None = None,
        agent_runner_factory: Any | None = None,
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
        self.sandbox_runner: SandboxRunner = sandbox_runner or create_sandbox_runner(
            settings=self.settings,
            github_client=self.github_client,
        )
        self._agent_runner_factory = agent_runner_factory or create_agent_runner

        # OPA Policy Engine components
        self.opa_client = OPAClient(base_url=self.settings.opa_url)
        self.rego_compiler = RegoCompiler()
        self.policy_evaluator: PolicyEvaluator = OPAEvaluator(
            opa_client=self.opa_client,
            rego_compiler=self.rego_compiler,
        )
        self.risk_engine = RiskEngine()

        # LLM Gateway & Provider Registry setup
        self.provider_registry = ProviderRegistry()
        configured_providers = self._register_default_llm_providers()

        llm_gw_config = LLMGatewayConfig(
            providers=configured_providers,
            default_primary=LLMProviderName.GEMINI,
            default_fallback=LLMProviderName.GROQ,
            routing_strategy=RoutingStrategy.TASK_BASED,
        )
        self.llm_gateway = LLMGateway(
            config=llm_gw_config,
            provider_registry=self.provider_registry,
            output_validator=OutputValidator(),
        )
        self.notification_gateway = NotificationGateway(
            slack_webhook_url=self.settings.slack_webhook_url,
            discord_webhook_url=self.settings.discord_webhook_url,
            dashboard_base_url=self.settings.dashboard_base_url,
        )


    def _register_default_llm_providers(self) -> dict[LLMProviderName, LLMProviderConfig]:
        """Register configured LLM provider plugins into the ProviderRegistry and return config map."""
        configs: dict[LLMProviderName, LLMProviderConfig] = {}

        # 1. Gemini (Primary reasoning and code generation)
        if self.settings.gemini_api_key:
            gemini_cfg = LLMProviderConfig(
                name=LLMProviderName.GEMINI,
                api_key=self.settings.gemini_api_key,
                models=[m.strip() for m in self.settings.gemini_models.split(",") if m.strip()],
                role="primary",
                task_types=[TaskType.REASONING, TaskType.CODE_GENERATION, TaskType.GENERAL],
            )
            self.provider_registry.register(GeminiProvider(config=gemini_cfg))
            configs[LLMProviderName.GEMINI] = gemini_cfg

        # 2. Groq (Fast classification and formatting)
        if self.settings.groq_api_key:
            groq_cfg = LLMProviderConfig(
                name=LLMProviderName.GROQ,
                api_key=self.settings.groq_api_key,
                base_url=self.settings.groq_base_url,
                models=[m.strip() for m in self.settings.groq_models.split(",") if m.strip()],
                role="fallback",
                task_types=[TaskType.CLASSIFICATION, TaskType.FORMATTING, TaskType.GENERAL],
            )
            self.provider_registry.register(GroqProvider(config=groq_cfg))
            configs[LLMProviderName.GROQ] = groq_cfg

        # 3. NVIDIA NIM (Fallback reasoning)
        if self.settings.nvidia_nim_api_key:
            nim_cfg = LLMProviderConfig(
                name=LLMProviderName.NVIDIA_NIM,
                api_key=self.settings.nvidia_nim_api_key,
                base_url=self.settings.nvidia_nim_base_url,
                models=[m.strip() for m in self.settings.nvidia_nim_models.split(",") if m.strip()],
                role="fallback",
                task_types=[TaskType.REASONING, TaskType.CODE_GENERATION, TaskType.GENERAL],
            )
            self.provider_registry.register(NVIDIANIMProvider(config=nim_cfg))
            configs[LLMProviderName.NVIDIA_NIM] = nim_cfg

        # 4. Fallback mock provider config if no API keys are provided in environment
        if not configs:
            mock_cfg = LLMProviderConfig(
                name=LLMProviderName.GEMINI,
                api_key="mock",
                models=["gemini-2.0-flash"],
                role="primary",
                task_types=[TaskType.REASONING, TaskType.CODE_GENERATION, TaskType.GENERAL],
            )
            self.provider_registry.register(GeminiProvider(config=mock_cfg))
            configs[LLMProviderName.GEMINI] = mock_cfg

        return configs

    def get_run_repository(self, session: AsyncSession) -> RunRepository:
        """Create a request-scoped RunRepository bound to the current session."""
        return RunRepository(session)

    def get_webhook_repository(self, session: AsyncSession) -> WebhookRepository:
        """Create a request-scoped WebhookRepository bound to the current session."""
        return WebhookRepository(session)

    def get_event_repository(self, session: AsyncSession) -> EventRepository:
        """Create a request-scoped EventRepository bound to the current session."""
        return EventRepository(session)

    def get_policy_repository(self, session: AsyncSession) -> PolicyRepository:
        """Create a request-scoped PolicyRepository bound to the current session."""
        return PolicyRepository(session)

    def get_budget_engine(self, session: AsyncSession) -> BudgetEngine:
        """Create a request-scoped BudgetEngine injecting RunRepository."""
        run_repo = self.get_run_repository(session)
        return BudgetEngine(run_repo)

    def get_policy_gateway(self, session: AsyncSession) -> PolicyGateway:
        """Assemble a request-scoped PolicyGateway."""
        policy_repo = self.get_policy_repository(session)
        event_repo = self.get_event_repository(session)
        budget_engine = self.get_budget_engine(session)

        return PolicyGateway(
            policy_repository=policy_repo,
            event_repository=event_repo,
            policy_evaluator=self.policy_evaluator,
            risk_engine=self.risk_engine,
            budget_engine=budget_engine,
        )

    def get_tool_gateway(self, session: AsyncSession) -> ToolGateway:
        """Assemble a request-scoped ToolGateway."""
        policy_repo = self.get_policy_repository(session)
        event_repo = self.get_event_repository(session)

        return ToolGateway(
            github_client=self.github_client,
            sandbox_runner=self.sandbox_runner,
            policy_repository=policy_repo,
            event_repository=event_repo,
            llm_gateway=self.llm_gateway,
        )

    def get_run_coordinator(self, session: AsyncSession) -> RunCoordinator:
        """
        Assemble a request-scoped RunCoordinator with injected repositories,
        GitHub client, PolicyGateway, ToolGateway, and compiled agent runner.
        """
        run_repo = self.get_run_repository(session)
        event_repo = self.get_event_repository(session)
        policy_gateway = self.get_policy_gateway(session)
        tool_gateway = self.get_tool_gateway(session)
        approval_service = self.get_approval_service(session)

        # Pass gateways to the agent runner factory
        runner = self._agent_runner_factory(
            self.github_client,
            event_repo,
            policy_gateway,
            tool_gateway,
            self.llm_gateway,
            approval_service,
        )

        return RunCoordinator(
            session=session,
            run_repository=run_repo,
            event_repository=event_repo,
            github_client=self.github_client,
            agent_runner=runner,
        )

    def get_webhook_service(self, session: AsyncSession) -> WebhookService:
        """Assemble a request-scoped WebhookService."""
        webhook_repo = self.get_webhook_repository(session)
        run_coordinator = self.get_run_coordinator(session)

        return WebhookService(
            webhook_repository=webhook_repo,
            run_coordinator=run_coordinator,
            webhook_secret=self.settings.github_webhook_secret,
        )

    def get_approval_repository(self, session: AsyncSession) -> ApprovalRepository:
        """Assemble a request-scoped ApprovalRepository."""
        return ApprovalRepository(session=session)

    def get_approval_service(self, session: AsyncSession) -> ApprovalService:
        """Assemble a request-scoped ApprovalService."""
        approval_repo = self.get_approval_repository(session)
        run_repo = self.get_run_repository(session)
        event_repo = self.get_event_repository(session)
        tool_gateway = self.get_tool_gateway(session)

        return ApprovalService(
            approval_repository=approval_repo,
            run_repository=run_repo,
            event_repository=event_repo,
            tool_gateway=tool_gateway,
            notification_gateway=self.notification_gateway,
        )


    async def aclose(self) -> None:
        """Gracefully dispose of database connection pools and external clients."""
        if hasattr(self.github_client, "aclose"):
            await cast(AsyncGitHubClient, self.github_client).aclose()
        await self.engine.dispose()


# Global application container instance
container = Container()
