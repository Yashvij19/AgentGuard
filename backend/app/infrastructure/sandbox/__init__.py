"""
Sandbox Execution Layer Package.
Provides isolated, disposable execution environments using the Strategy Pattern:
- E2BSandboxRunner (Default: fast ephemeral microVMs)
- GitHubActionsSandboxRunner (Fallback: native GitHub Actions CI runners)
"""

import structlog

from app.config import Settings
from app.config import settings as app_settings
from app.domain.protocols.github_client import GitHubClient
from app.domain.protocols.sandbox_runner import SandboxRunner
from app.infrastructure.sandbox.e2b_runner import E2BSandboxRunner
from app.infrastructure.sandbox.github_actions_runner import GitHubActionsSandboxRunner

logger = structlog.get_logger(__name__)

__all__ = [
    "E2BSandboxRunner",
    "GitHubActionsSandboxRunner",
    "create_sandbox_runner",
]


def create_sandbox_runner(
    settings: Settings | None = None,
    github_client: GitHubClient | None = None,
) -> SandboxRunner:
    """
    Factory function resolving the active SandboxRunner strategy based on application configuration.

    Args:
        settings: Application settings (defaults to global app_settings).
        github_client: Optional GitHub client required if using GitHub Actions fallback.

    Returns:
        Configured instance implementing SandboxRunner protocol.
    """
    cfg = settings or app_settings
    provider = cfg.sandbox_provider.lower().strip()

    if provider == "github_actions":
        logger.info("sandbox_runner_selected", provider="github_actions")
        return GitHubActionsSandboxRunner(github_client=github_client)

    # Default to E2B ephemeral sandboxes
    logger.info("sandbox_runner_selected", provider="e2b")
    return E2BSandboxRunner(
        api_key=cfg.e2b_api_key,
        base_url=cfg.e2b_base_url,
    )
