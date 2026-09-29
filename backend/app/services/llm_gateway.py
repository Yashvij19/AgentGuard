"""
Unified LLM Gateway service.
Orchestrates task-based routing, circuit breaker failover, metrics accounting,
and self-healing output schema validation.
"""

from typing import Any, TypeVar
from uuid import UUID

import structlog
from pydantic import BaseModel

from app.domain.exceptions import (
    LLMAllProvidersFailedError,
    LLMOutputValidationError,
)
from app.domain.models.llm_config import (
    LLMGatewayConfig,
    LLMMessage,
    LLMProviderName,
    LLMResponse,
    NormalizedRequest,
    NormalizedResponse,
    RoutingStrategy,
    TaskType,
)
from app.domain.protocols.llm_provider import LLMProvider
from app.infrastructure.database.repositories.provider_health_repository import (
    ProviderHealthRepository,
)
from app.infrastructure.llm.circuit_breaker import CircuitBreaker
from app.infrastructure.llm.output_validator import OutputValidator
from app.services.provider_registry import ProviderRegistry

logger = structlog.get_logger()
T = TypeVar("T", bound=BaseModel)


class LLMGateway:
    """
    Central gateway for all agent-to-LLM interactions.
    Enforces high-availability failover and output correctness across multi-vendor providers.
    """

    def __init__(
        self,
        config: LLMGatewayConfig,
        provider_registry: ProviderRegistry,
        output_validator: OutputValidator | None = None,
        circuit_breakers: dict[LLMProviderName, CircuitBreaker] | None = None,
        provider_health_repo: ProviderHealthRepository | None = None,
        max_repair_retries: int = 2,
    ) -> None:
        self.config = config
        self.registry = provider_registry
        self.validator = output_validator or OutputValidator()
        self.health_repo = provider_health_repo
        self.max_repair_retries = max_repair_retries

        # Initialize or attach per-provider circuit breakers
        self._circuit_breakers: dict[LLMProviderName, CircuitBreaker] = circuit_breakers or {}
        for name in self.registry.list_providers():
            if name not in self._circuit_breakers:
                self._circuit_breakers[name] = CircuitBreaker(
                    provider_name=name.value,
                    failure_threshold=config.circuit_breaker_threshold,
                    window_seconds=config.circuit_breaker_window_seconds,
                )

    def get_circuit_breaker(self, provider_name: LLMProviderName) -> CircuitBreaker:
        """Retrieve the circuit breaker instance for a given provider."""
        if provider_name not in self._circuit_breakers:
            self._circuit_breakers[provider_name] = CircuitBreaker(
                provider_name=provider_name.value,
                failure_threshold=self.config.circuit_breaker_threshold,
                window_seconds=self.config.circuit_breaker_window_seconds,
            )
        return self._circuit_breakers[provider_name]

    def _resolve_candidates(self, task_type: TaskType) -> list[LLMProvider]:
        """
        Build a prioritized list of candidate providers based on the configured RoutingStrategy.
        """
        candidates: list[LLMProvider] = []
        seen_names: set[LLMProviderName] = set()

        def add_provider(name: LLMProviderName) -> None:
            if name not in seen_names and self.registry.is_registered(name):
                candidates.append(self.registry.get(name))
                seen_names.add(name)

        if self.config.routing_strategy == RoutingStrategy.TASK_BASED:
            # 1. Specialists registered for this specific task
            for provider in self.registry.get_for_task(task_type):
                add_provider(provider.name)

            # 2. Configured primary provider
            add_provider(self.config.default_primary)

            # 3. Configured fallback provider
            add_provider(self.config.default_fallback)

        elif self.config.routing_strategy == RoutingStrategy.PRIMARY_FALLBACK:
            add_provider(self.config.default_primary)
            add_provider(self.config.default_fallback)

        # 4. Any remaining registered providers as emergency backups
        for name in self.registry.list_providers():
            add_provider(name)

        return candidates

    async def generate(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        run_id: UUID | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """
        Execute completion with automatic circuit breaker check and multi-provider failover.
        """
        candidates = self._resolve_candidates(task_type)
        if not candidates:
            raise LLMAllProvidersFailedError(
                f"No LLM providers available or registered for task: {task_type.value}"
            )

        last_error: Exception | None = None
        attempted_providers: list[str] = []

        for provider in candidates:
            breaker = self.get_circuit_breaker(provider.name)
            attempted_providers.append(provider.name.value)

            # 1. Circuit Breaker Admission Control
            if not await breaker.can_execute():
                logger.warning(
                    "llm_gateway.circuit_open_skipping",
                    provider=provider.name.value,
                    task_type=task_type.value,
                    run_id=str(run_id) if run_id else None,
                )
                continue

            # 2. Build normalized request for this candidate's primary model
            model = provider.default_model
            request = NormalizedRequest(
                messages=[LLMMessage(role="user", content=prompt)],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
                response_format=response_format,
            )

            # 3. Attempt Generation
            try:
                norm_resp: NormalizedResponse = await provider.generate(request)
                await breaker.record_success()

                logger.info(
                    "llm_gateway.generation_success",
                    provider=provider.name.value,
                    model=model,
                    task_type=task_type.value,
                    total_tokens=norm_resp.total_tokens,
                    latency_ms=norm_resp.latency_ms,
                    estimated_cost_usd=float(norm_resp.estimated_cost_usd),
                    run_id=str(run_id) if run_id else None,
                )

                return LLMResponse(
                    content=norm_resp.content,
                    model=norm_resp.model,
                    provider=norm_resp.provider,
                    prompt_tokens=norm_resp.prompt_tokens,
                    completion_tokens=norm_resp.completion_tokens,
                    total_tokens=norm_resp.total_tokens,
                    latency_ms=norm_resp.latency_ms,
                    estimated_cost_usd=norm_resp.estimated_cost_usd,
                )

            except Exception as err:
                await breaker.record_failure()
                last_error = err
                logger.warning(
                    "llm_gateway.provider_failed_failing_over",
                    failed_provider=provider.name.value,
                    error=str(err),
                    task_type=task_type.value,
                    run_id=str(run_id) if run_id else None,
                )

        raise LLMAllProvidersFailedError(
            f"All LLM providers failed for task {task_type.value}. "
            f"Attempted: {attempted_providers}. Last error: {last_error}"
        ) from last_error

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        task_type: TaskType = TaskType.GENERAL,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        run_id: UUID | None = None,
    ) -> T:
        """
        Generate structured output adhering to a Pydantic schema.
        Includes an automatic self-healing repair loop on validation failures.
        """
        current_prompt = prompt
        last_validation_error: str | None = None

        for attempt in range(self.max_repair_retries + 1):
            response = await self.generate(
                prompt=current_prompt,
                task_type=task_type,
                system_prompt=system_prompt,
                temperature=temperature,
                run_id=run_id,
            )

            try:
                return self.validator.parse_and_validate(response.content, response_model)
            except LLMOutputValidationError as err:
                last_validation_error = err.message
                logger.warning(
                    "llm_gateway.structured_validation_failed",
                    attempt=attempt + 1,
                    max_retries=self.max_repair_retries,
                    error=err.message,
                    run_id=str(run_id) if run_id else None,
                )

                if attempt < self.max_repair_retries:
                    # Construct repair prompt with exact schema and previous invalid output
                    current_prompt = self.validator.build_repair_prompt(
                        original_output=response.content,
                        error_message=err.message,
                        response_model=response_model,
                    )

        raise LLMOutputValidationError(
            f"Failed to produce valid {response_model.__name__} after "
            f"{self.max_repair_retries + 1} attempts. Last error: {last_validation_error}"
        )
