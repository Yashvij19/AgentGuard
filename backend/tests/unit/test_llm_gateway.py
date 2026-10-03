"""
Unit tests for the Unified LLM Gateway.
Tests task-based routing, circuit breaker failover, and self-healing output validation.
"""

from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from app.domain.exceptions import (
    LLMAllProvidersFailedError,
    LLMProviderError,
)
from app.domain.models.llm_config import (
    LLMGatewayConfig,
    LLMProviderConfig,
    LLMProviderName,
    NormalizedRequest,
    RoutingStrategy,
    TaskType,
)
from app.domain.models.provider_health import CircuitState
from app.infrastructure.llm.base_provider import BaseLLMProvider
from app.services.llm_gateway import LLMGateway
from app.services.provider_registry import ProviderRegistry


class MockProvider(BaseLLMProvider):
    """Test double implementing BaseLLMProvider for deterministic unit testing."""

    def __init__(
        self, name: LLMProviderName, task_types: list[TaskType], model: str = "test-model"
    ) -> None:
        config = LLMProviderConfig(
            name=name,
            api_key="mock_key",
            models=[model],
            role="primary",
            task_types=task_types,
        )
        super().__init__(config=config)
        self.mock_call = AsyncMock()

    async def _call_provider(self, request: NormalizedRequest) -> tuple[str, int, int, str]:
        return await self.mock_call(request)

    async def health_check(self) -> bool:
        return True


class TargetSchema(BaseModel):
    summary: str
    confidence: float


@pytest.fixture
def gateway_setup() -> tuple[LLMGateway, MockProvider, MockProvider]:
    registry = ProviderRegistry()

    # Gemini: specialist in REASONING and CODE_GENERATION
    gemini = MockProvider(
        name=LLMProviderName.GEMINI,
        task_types=[TaskType.REASONING, TaskType.CODE_GENERATION],
        model="gemini-2.0-flash",
    )
    # Groq: specialist in FORMATTING and CLASSIFICATION
    groq = MockProvider(
        name=LLMProviderName.GROQ,
        task_types=[TaskType.FORMATTING, TaskType.CLASSIFICATION],
        model="llama-3.3-70b-versatile",
    )

    registry.register(gemini)
    registry.register(groq)

    config = LLMGatewayConfig(
        providers={gemini.name: gemini.config, groq.name: groq.config},
        routing_strategy=RoutingStrategy.TASK_BASED,
        default_primary=LLMProviderName.GEMINI,
        default_fallback=LLMProviderName.GROQ,
    )

    gateway = LLMGateway(config=config, provider_registry=registry)
    return gateway, gemini, groq


@pytest.mark.asyncio
async def test_routing_routes_by_task_type(
    gateway_setup: tuple[LLMGateway, MockProvider, MockProvider],
) -> None:
    gateway, gemini, groq = gateway_setup

    gemini.mock_call.return_value = ("Reasoning result", 10, 20, "stop")
    groq.mock_call.return_value = ("Formatting result", 5, 10, "stop")

    # 1. REASONING task should route to Gemini first
    resp_reasoning = await gateway.generate("Analyze this PR", task_type=TaskType.REASONING)
    assert resp_reasoning.provider == LLMProviderName.GEMINI
    assert resp_reasoning.content == "Reasoning result"
    gemini.mock_call.assert_called_once()

    # 2. FORMATTING task should route to Groq first
    resp_formatting = await gateway.generate("Format this summary", task_type=TaskType.FORMATTING)
    assert resp_formatting.provider == LLMProviderName.GROQ
    assert resp_formatting.content == "Formatting result"
    groq.mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_failover_when_primary_fails(
    gateway_setup: tuple[LLMGateway, MockProvider, MockProvider],
) -> None:
    gateway, gemini, groq = gateway_setup

    # Gemini throws 429 Rate Limit error
    gemini.mock_call.side_effect = LLMProviderError("HTTP 429 Too Many Requests")
    # Groq succeeds as fallback
    groq.mock_call.return_value = ("Fallback successful response", 15, 25, "stop")

    response = await gateway.generate("Perform deep investigation", task_type=TaskType.REASONING)

    # Verify failover to Groq succeeded
    assert response.provider == LLMProviderName.GROQ
    assert response.content == "Fallback successful response"
    assert gemini.mock_call.call_count == 1
    assert groq.mock_call.call_count == 1


@pytest.mark.asyncio
async def test_failover_skips_provider_if_circuit_is_open(
    gateway_setup: tuple[LLMGateway, MockProvider, MockProvider],
) -> None:
    gateway, gemini, groq = gateway_setup

    # Manually trip Gemini's circuit breaker to OPEN
    gemini_breaker = gateway.get_circuit_breaker(LLMProviderName.GEMINI)
    gemini_breaker._state = CircuitState.OPEN

    groq.mock_call.return_value = ("Immediate fallback without waiting", 10, 10, "stop")

    response = await gateway.generate("Perform deep investigation", task_type=TaskType.REASONING)

    assert response.provider == LLMProviderName.GROQ
    # Gemini should NOT have been called at all!
    assert gemini.mock_call.call_count == 0
    assert groq.mock_call.call_count == 1


@pytest.mark.asyncio
async def test_structured_generation_with_self_healing_repair(
    gateway_setup: tuple[LLMGateway, MockProvider, MockProvider],
) -> None:
    gateway, gemini, _ = gateway_setup

    # Attempt 1 returns broken JSON. Attempt 2 returns valid JSON after repair prompt.
    gemini.mock_call.side_effect = [
        ("I think the summary is: {not valid json}", 10, 10, "stop"),
        ('{"summary": "Fixed valid summary", "confidence": 0.95}', 15, 15, "stop"),
    ]

    result: TargetSchema = await gateway.generate_structured(
        prompt="Summarize the PR changes",
        response_model=TargetSchema,
        task_type=TaskType.REASONING,
    )

    assert isinstance(result, TargetSchema)
    assert result.summary == "Fixed valid summary"
    assert result.confidence == 0.95
    assert gemini.mock_call.call_count == 2


@pytest.mark.asyncio
async def test_all_providers_failed_raises_exception(
    gateway_setup: tuple[LLMGateway, MockProvider, MockProvider],
) -> None:
    gateway, gemini, groq = gateway_setup

    gemini.mock_call.side_effect = LLMProviderError("Gemini down")
    groq.mock_call.side_effect = LLMProviderError("Groq down")

    with pytest.raises(LLMAllProvidersFailedError):
        await gateway.generate("Task requiring execution", task_type=TaskType.REASONING)
