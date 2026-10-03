"""
Policy Configuration domain models.
Defines the Pydantic schema for parsing and validating repo policy YAML files.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class CapabilityConfig(BaseModel):
    """Fine-grained capability permission buckets."""

    model_config = ConfigDict(frozen=True)

    allow: list[str] = Field(
        default_factory=lambda: [
            "github.read_file",
            "github.read_pr",
            "github.comment_pr",
            "commands.exec",
        ],
        description="Capabilities allowed to execute autonomously",
    )
    approval: list[str] = Field(
        default_factory=lambda: [
            "github.create_commit",
            "github.create_pr",
        ],
        description="Capabilities requiring human approval before execution",
    )
    deny: list[str] = Field(
        default_factory=lambda: [
            "github.delete_repository",
            "github.manage_webhooks",
            "github.admin",
        ],
        description="Capabilities strictly forbidden from executing",
    )


class FilesystemConfig(BaseModel):
    """Filesystem access boundaries using glob patterns."""

    model_config = ConfigDict(frozen=True)

    read: list[str] = Field(
        default_factory=lambda: ["**", "**/*"],
        description="Glob patterns for files the agent is permitted to read",
    )
    write: list[str] = Field(
        default_factory=lambda: ["**", "**/*"],
        description="Glob patterns for files the agent is permitted to modify or create",
    )


class CommandConfig(BaseModel):
    """Permitted and denied shell command patterns."""

    model_config = ConfigDict(frozen=True)

    allow: list[str] = Field(
        default_factory=lambda: [
            "^pytest.*",
            "^poetry run pytest.*",
            "^npm test.*",
            "^ruff check.*",
            "^python.*",
        ],
        description="Regex or prefix patterns for permitted shell commands",
    )
    deny: list[str] = Field(
        default_factory=lambda: [
            ".*rm -rf.*",
            ".*curl.*|.*sh",
            ".*wget.*|.*sh",
            ".*git push.*--force.*",
        ],
        description="Regex or prefix patterns for strictly forbidden commands",
    )


class NetworkConfig(BaseModel):
    """Network egress boundaries."""

    model_config = ConfigDict(frozen=True)

    allowed_domains: list[str] = Field(
        default_factory=lambda: [
            "api.github.com",
            "pypi.org",
        ],
        description="Permitted outbound HTTP/API destination domains",
    )


class ResourceLimitsConfig(BaseModel):
    """Execution resource constraints."""

    model_config = ConfigDict(frozen=True)

    max_execution_time_seconds: int = Field(
        default=300,
        gt=0,
        description="Maximum wall-clock execution time per run",
    )
    max_files_modified: int = Field(
        default=10,
        gt=0,
        description="Maximum number of files an agent can touch in a single run",
    )


class RiskThresholdConfig(BaseModel):
    """Risk score boundaries mapping to decision states."""

    model_config = ConfigDict(frozen=True)

    require_approval: int = Field(
        default=60,
        ge=0,
        le=100,
        description="Risk score at or above which human approval is mandatory",
    )
    deny: int = Field(
        default=90,
        ge=0,
        le=100,
        description="Risk score at or above which the action is immediately denied",
    )


class BudgetConfig(BaseModel):
    """Token, financial cost, and invocation limits for a run."""

    model_config = ConfigDict(frozen=True)

    max_tokens_per_run: int = Field(
        default=100_000,
        gt=0,
        description="Maximum total tokens (prompt + completion) consumed per run",
    )
    max_cost_usd_per_run: float = Field(
        default=1.00,
        ge=0.0,
        description="Maximum estimated cost in USD per run",
    )
    max_llm_calls_per_run: int = Field(
        default=25,
        gt=0,
        description="Maximum number of LLM API invocations allowed per run",
    )


class SensitiveActionTrigger(StrEnum):
    """Triggers that escalate actions to sensitive status."""

    FILE_PATTERN = "file_pattern"
    COMMAND_PATTERN = "command_pattern"
    OPERATION = "operation"


class SensitiveActionRule(BaseModel):
    """Explicit rule defining sensitive operations requiring human oversight."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Human-readable rule name")
    trigger: SensitiveActionTrigger = Field(description="Evaluation mechanism")
    pattern: str = Field(description="Target pattern (e.g. glob, regex, or verb)")
    description: str = Field(default="", description="Explanation for audit logs")


class PolicyConfig(BaseModel):
    """
    Complete parsed repository security policy.
    Maps directly to the enterprise policy YAML file.
    """

    model_config = ConfigDict(frozen=True)

    version: int = Field(
        default=1,
        ge=1,
        description="Schema specification version",
    )
    capabilities: CapabilityConfig = Field(
        default_factory=CapabilityConfig,
        description="Capability permission lists",
    )
    filesystem: FilesystemConfig = Field(
        default_factory=FilesystemConfig,
        description="Filesystem access boundaries",
    )
    commands: CommandConfig = Field(
        default_factory=CommandConfig,
        description="Command execution controls",
    )
    network: NetworkConfig = Field(
        default_factory=NetworkConfig,
        description="Outbound network access permissions",
    )
    resources: ResourceLimitsConfig = Field(
        default_factory=ResourceLimitsConfig,
        description="Resource allocation limits",
    )
    risk_weights: dict[str, int] = Field(
        default_factory=dict,
        description="Arbitrary risk weight mapping for actions or file types",
    )
    risk_thresholds: RiskThresholdConfig = Field(
        default_factory=RiskThresholdConfig,
        description="Risk score action thresholds",
    )
    budget: BudgetConfig = Field(
        default_factory=BudgetConfig,
        description="Run cost and token limits",
    )
    sensitive_actions: list[SensitiveActionRule] = Field(
        default_factory=list,
        description="High-sensitivity interception rules",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional enterprise metadata (e.g. owner, team, tier)",
    )


class Policy(BaseModel):
    """
    Persisted policy entity representing a repository's governance configuration.
    """

    model_config = ConfigDict(frozen=True)
    id: UUID = Field(
        default_factory=uuid4,
        description="Unique policy identifier",
    )
    repo: str = Field(
        description="Repository identifier in owner/repo format",
    )
    yaml_content: str = Field(
        description="Raw YAML policy source string",
    )
    rego_bundle: str | None = Field(
        default=None,
        description="Compiled Rego bundle or data payload",
    )
    parsed_content: PolicyConfig = Field(
        description="Validated structured policy configuration",
    )
    version: int = Field(
        default=1,
        ge=1,
        description="Monotonically increasing version number",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when first registered",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when last updated",
    )
