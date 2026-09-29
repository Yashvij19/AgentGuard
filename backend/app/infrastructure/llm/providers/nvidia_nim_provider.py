"""
NVIDIA NIM (Inference Microservice) provider adapter.
Default endpoint: https://integrate.api.nvidia.com/v1
"""

from typing import Any

import httpx

from app.domain.models.llm_config import (
    LLMProviderConfig,
    LLMProviderName,
    TaskType,
)
from app.infrastructure.llm.providers.openai_compat_provider import OpenAICompatProvider

NVIDIA_NIM_DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_NIM_DEFAULT_MODELS = ["meta/llama-3.1-8b-instruct"]


class NVIDIANIMProvider(OpenAICompatProvider):
    """
    NVIDIA NIM adapter.
    Operates as an OpenAI-compatible endpoint for hosted open-weights models.
    """

    def __init__(
        self,
        config: LLMProviderConfig | None = None,
        api_key: str = "",
        base_url: str = NVIDIA_NIM_DEFAULT_BASE_URL,
        models: list[str] | None = None,
        http_client: httpx.AsyncClient | None = None,
        **kwargs: Any,
    ) -> None:
        effective_config = config or LLMProviderConfig(
            name=LLMProviderName.NVIDIA_NIM,
            api_key=api_key,
            base_url=base_url,
            models=models or NVIDIA_NIM_DEFAULT_MODELS,
            role="fallback",
            task_types=[
                TaskType.REASONING,
                TaskType.GENERAL,
            ],
            timeout_seconds=30,
        )

        super().__init__(config=effective_config, http_client=http_client, **kwargs)
