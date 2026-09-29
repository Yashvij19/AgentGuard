"""
Request and response normalization engine.
Transforms diverse provider inputs/outputs to standardized domain models.
"""

from typing import Any

from app.domain.models.llm_config import (
    LLMProviderName,
    NormalizedRequest,
    NormalizedResponse,
)
from app.infrastructure.llm.cost_calculator import CostCalculator


class RequestNormalizer:
    """
    Translates between domain-level normalized I/O structures and vendor payloads.
    Ensures zero vendor-SDK types bleed into the core application layer.
    """

    def __init__(self, cost_calculator: CostCalculator | None = None) -> None:
        self.cost_calculator = cost_calculator or CostCalculator()

    @staticmethod
    def build_openai_messages(request: NormalizedRequest) -> list[dict[str, str]]:
        """
        Format NormalizedRequest messages into OpenAI/Groq/NIM compatible chat dicts.
        Injects system_prompt at index 0 if specified.
        """
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})

        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

        return messages

    @staticmethod
    def build_gemini_contents(request: NormalizedRequest) -> tuple[str | None, list[dict[str, Any]]]:
        """
        Format NormalizedRequest messages into Google Gemini content structures.
        Returns a tuple: (system_instruction, contents).
        """
        system_instruction = request.system_prompt
        contents: list[dict[str, Any]] = []

        for msg in request.messages:
            # Gemini maps 'assistant' role to 'model'
            role = "model" if msg.role == "assistant" else "user"
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}],
            })

        return system_instruction, contents

    def build_normalized_response(
        self,
        content: str,
        model: str,
        provider: LLMProviderName,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        finish_reason: str = "stop",
    ) -> NormalizedResponse:
        """
        Construct a fully calculated NormalizedResponse with token cost metrics.
        """
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = self.cost_calculator.calculate_cost(
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        return NormalizedResponse(
            content=content,
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            estimated_cost_usd=estimated_cost,
        )
