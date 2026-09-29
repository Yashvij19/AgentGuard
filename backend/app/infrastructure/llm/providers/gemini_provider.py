"""
Google Gemini provider adapter.
Communicates directly with Google Generative Language REST API via async httpx.
Primary provider for heavy reasoning, multi-file investigation, and code generation.
"""

from typing import Any

import httpx

from app.domain.exceptions import LLMProviderError
from app.domain.models.llm_config import (
    LLMProviderConfig,
    LLMProviderName,
    NormalizedRequest,
    TaskType,
)
from app.infrastructure.llm.base_provider import BaseLLMProvider

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_DEFAULT_MODELS = ["gemini-2.0-flash", "gemini-1.5-pro"]


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini adapter using the v1beta generateContent REST endpoint.
    """

    def __init__(
        self,
        config: LLMProviderConfig | None = None,
        api_key: str = "",
        models: list[str] | None = None,
        http_client: httpx.AsyncClient | None = None,
        **kwargs: Any,
    ) -> None:
        effective_config = config or LLMProviderConfig(
            name=LLMProviderName.GEMINI,
            api_key=api_key,
            models=models or GEMINI_DEFAULT_MODELS,
            role="primary",
            task_types=[
                TaskType.REASONING,
                TaskType.CODE_GENERATION,
                TaskType.GENERAL,
            ],
            timeout_seconds=45,
        )
        super().__init__(config=effective_config, **kwargs)
        self._client = http_client or httpx.AsyncClient(timeout=effective_config.timeout_seconds)

    async def _call_provider(
        self,
        request: NormalizedRequest,
    ) -> tuple[str, int, int, str]:
        """
        Execute completion against the Google Gemini REST API.
        """
        endpoint = f"{GEMINI_API_BASE}/models/{request.model}:generateContent"
        headers = {
            "x-goog-api-key": self.config.api_key,
            "Content-Type": "application/json",
        }

        # Transform NormalizedRequest messages into Gemini structure
        system_instruction, contents = self.normalizer.build_gemini_contents(request)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }

        if system_instruction:
            payload["system_instruction"] = {
                "parts": [{"text": system_instruction}]
            }

        try:
            response = await self._client.post(endpoint, json=payload, headers=headers)
        except httpx.TimeoutException as err:
            raise LLMProviderError(
                f"Timeout ({self.config.timeout_seconds}s) connecting to Gemini at {endpoint}"
            ) from err
        except httpx.RequestError as err:
            raise LLMProviderError(f"Network error connecting to Gemini: {err}") from err

        if response.is_error:
            error_body = response.text[:300]
            raise LLMProviderError(
                f"Gemini API returned HTTP {response.status_code}: {error_body}"
            )

        data = response.json()
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMProviderError(
                    f"Gemini returned empty candidates list (possibly blocked by safety filters): {data}"
                )

            candidate = candidates[0]
            finish_reason = candidate.get("finishReason", "STOP").lower()
            parts = candidate.get("content", {}).get("parts", [])
            content = parts[0].get("text", "") if parts else ""

            # Token accounting from usageMetadata
            usage = data.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", 0)
            completion_tokens = usage.get("candidatesTokenCount", 0)

            return content, prompt_tokens, completion_tokens, finish_reason

        except (KeyError, IndexError) as err:
            raise LLMProviderError(
                f"Malformed response payload from Gemini: {data}"
            ) from err

    async def health_check(self) -> bool:
        """Probe Gemini models list endpoint to confirm liveness and credentials."""
        endpoint = f"{GEMINI_API_BASE}/models"
        headers = {"x-goog-api-key": self.config.api_key}
        try:
            response = await self._client.get(endpoint, headers=headers, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
