"""
Unit tests for the Sandbox Execution Layer.
Verifies E2B runner simulation, timeout handling, GitHub Actions fallback, and strategy factory.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.infrastructure.sandbox import (
    E2BSandboxRunner,
    GitHubActionsSandboxRunner,
    create_sandbox_runner,
)


@pytest.mark.asyncio
async def test_e2b_runner_mock_execution_success() -> None:
    """E2B runner in mock mode executes command and returns clean SandboxResult."""
    runner = E2BSandboxRunner(api_key="mock")

    result = await runner.run_command("pytest tests/", timeout_seconds=10)

    assert result.exit_code == 0
    assert not result.timed_out
    assert "[E2B Mock]" in result.stdout
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_e2b_runner_mock_execution_failure() -> None:
    """E2B mock simulation simulates exit code 1 when command indicates test failure."""
    runner = E2BSandboxRunner(api_key="mock")

    result = await runner.run_command("pytest tests/test_failing.py", timeout_seconds=10)

    assert result.exit_code == 1
    assert "Mock test failure triggered" in result.stderr


@pytest.mark.asyncio
async def test_e2b_runner_timeout_handling() -> None:
    """When command exceeds timeout, runner must return exit code 124 and timed_out=True."""
    mock_client = AsyncMock()
    # Mock synchronous response object
    create_resp = MagicMock()
    create_resp.json.return_value = {"sandboxID": "sbx-test-123"}
    create_resp.raise_for_status.return_value = None
    # mock_client.post returns create_resp first, then raises TimeoutError on exec
    mock_client.post = AsyncMock(side_effect=[create_resp, TimeoutError()])
    mock_client.delete = AsyncMock()
    runner = E2BSandboxRunner(api_key="live_key", http_client=mock_client)
    result = await runner.run_command("sleep 100", timeout_seconds=1)
    assert result.timed_out
    assert result.exit_code == 124
    assert "timed out" in result.stderr.lower()
    # Verify sandbox was deleted in finally block
    mock_client.delete.assert_called_once()


@pytest.mark.asyncio
async def test_github_actions_runner_mock_execution() -> None:
    """GitHub Actions runner in mock mode returns completed SandboxResult."""
    runner = GitHubActionsSandboxRunner()

    result = await runner.run_command("npm test", timeout_seconds=5)

    assert result.exit_code == 0
    assert not result.timed_out
    assert "[GitHub Actions Mock]" in result.stdout


def test_create_sandbox_runner_factory_strategy() -> None:
    """create_sandbox_runner factory resolves strategy based on sandbox_provider setting."""
    # 1. Test E2B selection
    e2b_settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        github_app_id="123",
        github_webhook_secret="sec",
        github_private_key="key",
        sandbox_provider="e2b",
    )
    runner_e2b = create_sandbox_runner(settings=e2b_settings)
    assert isinstance(runner_e2b, E2BSandboxRunner)

    # 2. Test GitHub Actions selection
    gha_settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        github_app_id="123",
        github_webhook_secret="sec",
        github_private_key="key",
        sandbox_provider="github_actions",
    )
    runner_gha = create_sandbox_runner(settings=gha_settings)
    assert isinstance(runner_gha, GitHubActionsSandboxRunner)
