"""
E2B Sandbox Runner implementation.
Executes untrusted shell commands and tests inside isolated, ephemeral E2B microVMs.
Guarantees host isolation, hard timeouts, and resource destruction.
"""

import asyncio
import time
from typing import Any

import httpx
import structlog

from app.config import settings
from app.domain.protocols.sandbox_runner import SandboxResult, SandboxRunner

logger = structlog.get_logger(__name__)


class E2BSandboxRunner(SandboxRunner):
    """
    Executes commands inside ephemeral E2B sandboxes using async HTTP REST client.
    Guarantees that untrusted code never touches the backend host environment.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        template_id: str = "base",
    ) -> None:
        """
        Initialize the E2B runner with credentials and template ID.
        Args:
            api_key: E2B user API key (defaults to settings.e2b_api_key; empty enables mock mode).
            base_url: E2B API REST endpoint (defaults to settings.e2b_base_url).
            http_client: Optional injected httpx.AsyncClient for connection reuse / testing.
            template_id: E2B container template (default: 'base' with Python/Node runtime).
        """
        resolved_key = api_key if api_key is not None else settings.e2b_api_key
        resolved_url = base_url or settings.e2b_base_url
        self._api_key = resolved_key or ""
        self._base_url = resolved_url.rstrip("/")
        self._client = http_client or httpx.AsyncClient(timeout=30.0)
        self._template_id = template_id

    @property
    def is_mock_mode(self) -> bool:
        """True if running in mock/offline mode without a live E2B cloud token."""
        return not self._api_key or self._api_key in ("mock", "test", "disabled", "dummy_e2b_key")

    async def run_command(
        self,
        command: str,
        files: dict[str, str] | None = None,
        timeout_seconds: int = 60,
    ) -> SandboxResult:
        """
        Execute a shell command inside an ephemeral E2B sandbox container.
        Guarantees cleanup of the microVM in all circumstances.

        Args:
            command: Shell command string to execute (e.g. 'pytest tests/').
            files: Optional dictionary mapping relative paths to file contents.
            timeout_seconds: Maximum wall-clock seconds before terminating execution.

        Returns:
            SandboxResult with stdout, stderr, exit code, and execution duration.
        """
        start_time = time.monotonic()

        # 1. Fallback / Mock simulation mode for local dev and testing
        if self.is_mock_mode:
            logger.info("e2b_sandbox_mock_execution", command=command)
            await asyncio.sleep(0.05)  # Simulate container startup delay
            duration_ms = int((time.monotonic() - start_time) * 1000)

            # Deterministic simulation: fail if command targets a known failing scenario
            is_failing_test = "fail" in command.lower() or "error" in command.lower()
            return SandboxResult(
                exit_code=1 if is_failing_test else 0,
                stdout=f"[E2B Mock] Executed: {command}\nFiles mounted: {list((files or {}).keys())}",
                stderr="Mock test failure triggered" if is_failing_test else "",
                duration_ms=duration_ms,
                timed_out=False,
            )

        # 2. Live E2B Ephemeral Container Lifecycle
        sandbox_id: str | None = None
        headers = {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
        }

        try:
            # Step A: Create ephemeral sandbox
            create_resp = await self._client.post(
                f"{self._base_url}/sandboxes",
                headers=headers,
                json={"templateID": self._template_id},
                timeout=15.0,
            )
            create_resp.raise_for_status()
            sandbox_data = create_resp.json()
            sandbox_id = sandbox_data.get("sandboxID") or sandbox_data.get("id")

            # Step B: Upload files if provided
            if files and sandbox_id:
                for file_path, content in files.items():
                    await self._client.post(
                        f"{self._base_url}/sandboxes/{sandbox_id}/files",
                        headers=headers,
                        json={"path": file_path, "content": content},
                        timeout=10.0,
                    )

            # Step C: Execute command with bounded timeout
            exec_payload: dict[str, Any] = {
                "command": command,
                "timeout": timeout_seconds,
            }

            exec_resp = await asyncio.wait_for(
                self._client.post(
                    f"{self._base_url}/sandboxes/{sandbox_id}/commands",
                    headers=headers,
                    json=exec_payload,
                    timeout=float(timeout_seconds + 5),
                ),
                timeout=float(timeout_seconds + 5),
            )
            exec_resp.raise_for_status()
            cmd_data = exec_resp.json()

            duration_ms = int((time.monotonic() - start_time) * 1000)
            return SandboxResult(
                exit_code=cmd_data.get("exitCode", 0),
                stdout=cmd_data.get("stdout", ""),
                stderr=cmd_data.get("stderr", ""),
                duration_ms=duration_ms,
                timed_out=False,
            )

        except TimeoutError:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.warning("e2b_sandbox_timed_out", command=command, timeout=timeout_seconds)
            return SandboxResult(
                exit_code=124,  # Standard POSIX timeout exit code
                stdout="",
                stderr=f"Command timed out after {timeout_seconds} seconds.",
                duration_ms=duration_ms,
                timed_out=True,
            )

        except Exception as err:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error("e2b_sandbox_execution_failed", error=str(err), command=command)
            return SandboxResult(
                exit_code=1,
                stdout="",
                stderr=f"Sandbox execution error: {err}",
                duration_ms=duration_ms,
                timed_out=False,
            )

        finally:
            # Step D: ALWAYS destroy the ephemeral sandbox to prevent resource leaks
            if sandbox_id:
                try:
                    await self._client.delete(
                        f"{self._base_url}/sandboxes/{sandbox_id}",
                        headers=headers,
                        timeout=5.0,
                    )
                    logger.debug("e2b_sandbox_destroyed", sandbox_id=sandbox_id)
                except Exception as cleanup_err:
                    logger.warning(
                        "e2b_sandbox_cleanup_failed", sandbox_id=sandbox_id, error=str(cleanup_err)
                    )

    async def health_check(self) -> bool:
        """Check availability of the E2B service endpoint."""
        if self.is_mock_mode:
            return True
        try:
            resp = await self._client.get(
                f"{self._base_url}/health",
                headers={"X-API-Key": self._api_key},
                timeout=5.0,
            )
            return resp.status_code == 200
        except Exception:
            return False
