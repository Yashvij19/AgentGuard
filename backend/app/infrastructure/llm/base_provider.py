"""
Abstract base class for all LLM provider adapters (The Plugin Chassis).
Enforces uniform lifecycle, metrics collection, and schema validation.
"""

import time
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from app.domain.models.llm_config import (
    LLMMessage,
    LLMProviderConfig,
    LLMProviderName,
    NormalizedRequest,
    NormalizedResponse,
    TaskType,
)
from app.infrastructure.llm.cost_calculator import CostCalculator
from app.infrastructure.llm.output_validator import OutputValidator
from app.infrastructure.llm.request_normalizer import RequestNormalizer

T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(ABC):
    """
    Base implementation of the LLMProvider protocol.
    Subclasses only need to implement `_call_provider` and `health_check`.
    """

    def __init__(
        self,
        config: LLMProviderConfig,
        request_normalizer: RequestNormalizer | None = None,
        output_validator: OutputValidator | None = None,
        cost_calculator: CostCalculator | None = None,
    ) -> None:
        self.config = config
        self.normalizer = request_normalizer or RequestNormalizer()
        self.validator = output_validator or OutputValidator()
        self.cost_calculator = cost_calculator or CostCalculator()

    @property
    def name(self) -> LLMProviderName:
        return self.config.name

    @property
    def supported_task_types(self) -> list[TaskType]:
        return self.config.task_types

    @property
    def default_model(self) -> str:
        """Return the primary configured model for this provider."""
        return self.config.models[0]


    @abstractmethod
    async def _call_provider(
        self,
        request: NormalizedRequest,
    ) -> tuple[str, int, int, str]:
        """
        Subclass hook: executes vendor-specific API request.
        Must return: (raw_content, prompt_tokens, completion_tokens, finish_reason).
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Probe upstream endpoint to confirm liveness and valid credentials."""
        ...

    async def generate(
        self,
        request: NormalizedRequest,
    ) -> NormalizedResponse:
        """
        Standard execution flow:
        1. Measure wall-clock latency
        2. Invoke subclass raw API call
        3. Build normalized response with token & cost calculation
        """
        start_time = time.perf_counter()

        content, prompt_tokens, completion_tokens, finish_reason = await self._call_provider(request)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        return self.normalizer.build_normalized_response(
            content=content,
            model=request.model,
            provider=self.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
        )

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.1,
    ) -> T:
        """
        Generate completion and validate against a target Pydantic schema.
        """
        primary_model = self.config.models[0]
        request = NormalizedRequest(
            messages=[LLMMessage(role="user", content=prompt)],
            model=primary_model,
            temperature=temperature,
            system_prompt=system_prompt,
        )

        response = await self.generate(request)
        return self.validator.parse_and_validate(response.content, response_model)

    def estimate_tokens(self, text: str) -> int:
        """
        Fast heuristic token count (approx. 4 characters per token).
        """
        if not text:
            return 0
        return max(1, len(text) // 4)

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate estimated cost using the provider's pricing configuration.
        """
        cost_dec = self.cost_calculator.calculate_cost(
            provider=self.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        return float(cost_dec)
