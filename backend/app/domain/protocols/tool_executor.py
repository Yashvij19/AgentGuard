"""
Protocol interface and execution models for the Tool Gateway execution layer.
"""

from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.domain.models.action_intent import ActionIntent


class ExecutionResult(BaseModel):
    """Standardized result emitted by any tool execution."""
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: int = Field(default=0, ge=0)
    tokens_used: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolExecutor(Protocol):
    """Interface for executing verified ActionIntents with scoped credentials."""

    async def execute(
        self,
        action_intent: ActionIntent,
    ) -> ExecutionResult:
        """Dispatch and execute an approved action intent."""
        ...
