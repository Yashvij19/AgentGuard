"""
Protocol interface and result models for sandboxed code execution.
Follows the Strategy Pattern (E2BSandboxRunner vs GitHubActionsSandboxRunner).
"""

from typing import Protocol

from pydantic import BaseModel, Field


class SandboxResult(BaseModel):
    """Outcome of command execution inside an isolated environment."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = Field(default=0, ge=0)
    timed_out: bool = False


class SandboxRunner(Protocol):
    """
    Abstract interface for isolated execution environments.
    Guarantees no untrusted code ever executes directly on the backend host.
    """

    async def run_command(
        self,
        command: str,
        files: dict[str, str] | None = None,
        timeout_seconds: int = 60,
    ) -> SandboxResult:
        """
        Execute a shell command inside an ephemeral sandbox container.
        """
        ...

    async def health_check(self) -> bool:
        """Check availability of the sandbox infrastructure provider."""
        ...
