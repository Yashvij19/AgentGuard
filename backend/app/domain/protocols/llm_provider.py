"""
Protocol interface for LLM provider adapters (The Plugin Contract).
Every adapter (Gemini, Groq, NVIDIA NIM, etc.) must fulfill this contract.
"""

from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.domain.models.llm_config import (
    LLMProviderName,
    NormalizedRequest,
    NormalizedResponse,
    TaskType,
)

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    """
    Formal interface for all LLM provider plugins.
    Enforces identical API surface across disparate provider SDKs.
    """

    @property
    def name(self) -> LLMProviderName:
        """Unique provider identifier."""
        ...

    @property
    def supported_task_types(self) -> list[TaskType]:
        """Task categories this provider is capable of handling."""
        ...

    @property
    def default_model(self) -> str:
        """Primary or default model identifier for this provider."""
        ...


    async def generate(
        self,
        request: NormalizedRequest,
    ) -> NormalizedResponse:
        """
        Execute completion with the underlying provider using normalized I/O.
        """
        ...

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.1,
    ) -> T:
        """
        Execute completion and parse directly into a validated Pydantic model.
        """
        ...

    async def health_check(self) -> bool:
        """Probe the upstream provider API for liveness and valid credentials."""
        ...

    def estimate_tokens(self, text: str) -> int:
        """Estimate token consumption for a string before dispatching."""
        ...

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost in USD based on provider pricing tables."""
        ...
