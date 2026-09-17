"""
Action Intent domain models.
Represents a structured, declarative proposal by an agent before any execution.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ActionType(StrEnum):
    """Supported agent action categories."""

    FILE_READ = "FILE_READ"
    FILE_WRITE = "FILE_WRITE"
    COMMAND_EXEC = "COMMAND_EXEC"
    NETWORK_REQUEST = "NETWORK_REQUEST"
    GITHUB_API = "GITHUB_API"
    LLM_CALL = "LLM_CALL"


class ActionIntent(BaseModel):
    """
    Immutable representation of an action the agent proposes to take.
    Must be evaluated by the Policy Gateway before execution.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this action intent",
    )
    run_id: UUID = Field(
        description="Reference to the run that originated this intent",
    )
    action: ActionType = Field(
        description="High-level category of the requested action",
    )
    target: str = Field(
        min_length=1,
        description="Target resource (e.g. file path, command string, API endpoint)",
    )
    operation: str = Field(
        min_length=1,
        description="Specific verb (e.g. read, modify, create, delete, execute)",
    )
    capability: str = Field(
        min_length=1,
        description="Fine-grained capability identifier (e.g. github.read_file, filesystem.write)",
    )
    reason: str = Field(
        min_length=1,
        description="Agent's explicit rationale for proposing this action",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional contextual metadata (e.g. diff contents, parameters)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the intent was generated",
    )


class ActionIntentBuilder:
    """
    Fluent builder utility for constructing valid ActionIntents from agent nodes.
    Prevents repetitive boilerplate in LangGraph state functions.
    """

    def __init__(self, run_id: UUID) -> None:
        self._run_id = run_id
        self._metadata: dict[str, Any] = {}

    def file_read(self, file_path: str, reason: str) -> ActionIntent:
        """Construct a FILE_READ intent."""
        return ActionIntent(
            run_id=self._run_id,
            action=ActionType.FILE_READ,
            target=file_path,
            operation="read",
            capability="github.read_file",
            reason=reason,
            metadata=self._metadata,
        )

    def file_write(
        self,
        file_path: str,
        operation: str,
        reason: str,
        diff: str | None = None,
    ) -> ActionIntent:
        """Construct a FILE_WRITE intent."""
        meta = dict(self._metadata)
        if diff:
            meta["diff"] = diff
        return ActionIntent(
            run_id=self._run_id,
            action=ActionType.FILE_WRITE,
            target=file_path,
            operation=operation,
            capability="github.create_commit",
            reason=reason,
            metadata=meta,
        )

    def github_comment(self, pr_number: int, reason: str, comment_preview: str) -> ActionIntent:
        """Construct a GITHUB_API intent for posting a PR comment."""
        meta = dict(self._metadata)
        meta["comment_preview"] = comment_preview
        return ActionIntent(
            run_id=self._run_id,
            action=ActionType.GITHUB_API,
            target=f"pull_requests/{pr_number}/comments",
            operation="comment",
            capability="github.comment_pr",
            reason=reason,
            metadata=meta,
        )
