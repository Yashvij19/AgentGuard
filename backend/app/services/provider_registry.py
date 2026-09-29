"""
Provider Registry for dynamic LLM plugin management.
Decouples provider discovery and task capability lookup from the gateway core.
"""

import asyncio

from app.domain.exceptions import LLMProviderError
from app.domain.models.llm_config import LLMProviderName, TaskType
from app.domain.protocols.llm_provider import LLMProvider


class ProviderRegistry:
    """
    In-memory registry of initialized LLM provider plugins.
    Enables dynamic registration and capability-based provider lookup.
    """

    def __init__(self) -> None:
        self._providers: dict[LLMProviderName, LLMProvider] = {}

    def register(self, provider: LLMProvider) -> None:
        """
        Register an LLM provider plugin.
        Overwrites any previous provider registered under the same name.
        """
        self._providers[provider.name] = provider

    def get(self, name: LLMProviderName) -> LLMProvider:
        """
        Retrieve a registered provider by its identifier.
        Raises LLMProviderError if the provider is not registered.
        """
        if name not in self._providers:
            available = [p.value for p in self._providers.keys()]
            raise LLMProviderError(
                f"LLM Provider '{name.value}' is not registered. Available providers: {available}"
            )
        return self._providers[name]

    def get_for_task(self, task_type: TaskType) -> list[LLMProvider]:
        """
        Retrieve all registered providers that support the specified TaskType.
        Returns empty list if no providers support the task.
        """
        return [
            provider
            for provider in self._providers.values()
            if task_type in provider.supported_task_types
        ]

    def list_providers(self) -> list[LLMProviderName]:
        """Return list of all registered provider names."""
        return list(self._providers.keys())

    def is_registered(self, name: LLMProviderName) -> bool:
        """Check whether a provider is registered."""
        return name in self._providers

    async def health_check_all(self) -> dict[LLMProviderName, bool]:
        """
        Concurrently probe upstream health for all registered providers.
        Returns a mapping of ProviderName -> is_healthy bool.
        """
        if not self._providers:
            return {}

        names = list(self._providers.keys())
        tasks = [provider.health_check() for provider in self._providers.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        status: dict[LLMProviderName, bool] = {}
        for name, result in zip(names, results, strict=True):
            status[name] = result is True

        return status
