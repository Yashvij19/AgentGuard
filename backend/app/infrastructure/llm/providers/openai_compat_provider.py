"""
OpenAI-compatible LLM provider adapter.
Communicates via standard /v1/chat/completions endpoint using pure async httpx.
Serves as the foundation for OpenAI, Groq, NVIDIA NIM, and self-hosted vLLM.
"""

from typing import Any

import httpx

from app.domain.exceptions import LLMProviderError
from app.domain.models.llm_config import (
    LLMProviderConfig,
    NormalizedRequest,
)
from app.infrastructure.llm.base_provider import BaseLLMProvider


class OpenAICompatProvider(BaseLLMProvider):
    """
    Standard adapter for any provider supporting OpenAI's REST API specification.
    """

    def __init__(
        self,
        config: LLMProviderConfig,
        http_client: httpx.AsyncClient | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(config=config, **kwargs)
        self.base_url = (config.base_url or "https://api.openai.com/v1").rstrip("/")
        self._client = http_client or httpx.AsyncClient(timeout=config.timeout_seconds)

    async def _call_provider(
        self,
        request: NormalizedRequest,
    ) -> tuple[str, int, int, str]:
        """
        Execute completion against the OpenAI-compatible endpoint.
        """
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        messages = self.normalizer.build_openai_messages(request)
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        if request.response_format:
            payload["response_format"] = request.response_format

        try:
            response = await self._client.post(endpoint, json=payload, headers=headers)
        except httpx.TimeoutException as err:
            raise LLMProviderError(
                f"Timeout ({self.config.timeout_seconds}s) connecting to {self.name} at {endpoint}"
            ) from err
        except httpx.RequestError as err:
            raise LLMProviderError(
                f"Network error connecting to {self.name}: {err}"
            ) from err

        if response.is_error:
            error_body = response.text[:300]
            raise LLMProviderError(
                f"Provider {self.name} returned HTTP {response.status_code}: {error_body}"
            )

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"] or ""
            finish_reason = data["choices"][0].get("finish_reason", "stop")
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            return content, prompt_tokens, completion_tokens, finish_reason
        except (KeyError, IndexError) as err:
            raise LLMProviderError(
                f"Malformed response payload from {self.name}: {data}"
            ) from err

    async def health_check(self) -> bool:
        """Probe the endpoint using a models list call or basic ping."""
        endpoint = f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        try:
            response = await self._client.get(endpoint, headers=headers, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
