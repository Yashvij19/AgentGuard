"""
Domain models for the Unified LLM Gateway.
Defines provider configurations, routing strategies, task types, pricing,
and normalized request/response contracts for multi-provider abstraction.
"""

from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class LLMProviderName(StrEnum):
    """Supported LLM provider plugin identifiers."""

    GEMINI = "gemini"
    GROQ = "groq"
    NVIDIA_NIM = "nvidia_nim"
    OPENAI_COMPAT = "openai_compat"


class TaskType(StrEnum):
    """
    Categorization of cognitive workloads.
    Enables task-based routing (e.g. reasoning -> Gemini, formatting -> Groq).
    """

    REASONING = "reasoning"
    CODE_GENERATION = "code_generation"
    CLASSIFICATION = "classification"
    FORMATTING = "formatting"
    GENERAL = "general"


class RoutingStrategy(StrEnum):
    """Strategies for provider selection and failover."""

    TASK_BASED = "task_based"
    PRIMARY_FALLBACK = "primary_fallback"
    ROUND_ROBIN = "round_robin"


class TokenPricing(BaseModel):
    """Pricing configuration in USD per 1,000 tokens."""

    input_per_1k: Decimal = Field(default=Decimal("0.0"), ge=0)
    output_per_1k: Decimal = Field(default=Decimal("0.0"), ge=0)


class LLMMessage(BaseModel):
    """Provider-agnostic chat message representation."""

    role: Literal["system", "user", "assistant"]
    content: str


class NormalizedRequest(BaseModel):
    """
    Standardized payload format passed into any LLM provider adapter.
    Decouples provider-specific SDK schemas from the gateway core.
    """

    messages: list[LLMMessage]
    model: str
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    response_format: dict[str, Any] | None = None
    system_prompt: str | None = None


class NormalizedResponse(BaseModel):
    """
    Standardized response returned by any LLM provider adapter.
    Includes full token and latency accounting for observability.
    """

    content: str
    model: str
    provider: LLMProviderName
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    finish_reason: str = "stop"
    estimated_cost_usd: Decimal = Field(default=Decimal("0.0"), ge=0)


class LLMResponse(BaseModel):
    """Client-facing response object from the LLM Gateway."""

    content: str
    model: str
    provider: LLMProviderName
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    estimated_cost_usd: Decimal
    raw_response: dict[str, Any] = Field(default_factory=dict)


class LLMProviderConfig(BaseModel):
    """Per-provider connection and behavioral configuration."""

    name: LLMProviderName
    api_key: str
    base_url: str | None = None
    models: list[str]
    role: Literal["primary", "fallback", "specialist"]
    task_types: list[TaskType]
    max_tokens: int = Field(default=4096, gt=0)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    timeout_seconds: int = Field(default=30, gt=0)
    max_retries: int = Field(default=3, ge=0)
    rate_limit_rpm: int | None = Field(default=None, gt=0)


class LLMGatewayConfig(BaseModel):
    """Global configuration governing multi-provider routing and resilience."""

    providers: dict[LLMProviderName, LLMProviderConfig]
    routing_strategy: RoutingStrategy = RoutingStrategy.TASK_BASED
    default_primary: LLMProviderName = LLMProviderName.GEMINI
    default_fallback: LLMProviderName = LLMProviderName.GROQ
    output_validation_enabled: bool = True
    circuit_breaker_threshold: float = Field(default=0.5, ge=0.1, le=1.0)
    circuit_breaker_window_seconds: int = Field(default=300, gt=0)

    @field_validator("providers")
    @classmethod
    def validate_providers_not_empty(
        cls, v: dict[LLMProviderName, LLMProviderConfig]
    ) -> dict[LLMProviderName, LLMProviderConfig]:
        if not v:
            raise ValueError("LLMGatewayConfig must have at least one configured provider")
        return v
