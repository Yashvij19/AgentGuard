"""
Groq LLM provider adapter (Fast inference specialist).
Receives endpoint URL, models, and credentials via LLMProviderConfig.
"""

from typing import Any

import httpx

from app.domain.models.llm_config import (
    LLMProviderConfig,
    LLMProviderName,
    TaskType,
)
from app.infrastructure.llm.providers.openai_compat_provider import OpenAICompatProvider


class GroqProvider(OpenAICompatProvider):
    """
    Groq adapter optimized for ultra-low latency formatting and classification tasks.
    Configured entirely via injected LLMProviderConfig.
    """

    def __init__(
        self,
        config: LLMProviderConfig | None = None,
        api_key: str = "",
        base_url: str = "https://api.groq.com/openai/v1",
        models: list[str] | None = None,
        http_client: httpx.AsyncClient | None = None,
        **kwargs: Any,
    ) -> None:
        effective_config = config or LLMProviderConfig(
            name=LLMProviderName.GROQ,
            api_key=api_key,
            base_url=base_url,
            models=models or ["llama-3.3-70b-versatile"],
            role="fallback",
            task_types=[
                TaskType.CLASSIFICATION,
                TaskType.FORMATTING,
                TaskType.GENERAL,
            ],
            timeout_seconds=20,
        )

        super().__init__(config=effective_config, http_client=http_client, **kwargs)
