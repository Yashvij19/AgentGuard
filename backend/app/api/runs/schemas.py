"""
Pydantic schemas for the Runs API endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.models.run import RunStatus, TriggerType
from app.domain.models.run_event import EventType


class RunResponse(BaseModel):
    """Schema representing an individual AgentGuard run."""

    id: UUID
    repo: str
    pr_number: int
    head_sha: str
    trigger_type: TriggerType
    status: RunStatus
    policy_version: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_tokens: int = 0
    total_cost_usd: Decimal = Decimal("0.000000")
    driver: str = "Google Gemini 2.5 Flash"
    created_at: datetime
    updated_at: datetime



class RunEventResponse(BaseModel):
    """Schema representing an audit event emitted during run execution."""

    id: UUID
    run_id: UUID
    step_name: str
    event_type: EventType
    content: dict[str, Any] = Field(default_factory=dict)
    tokens_used: int = 0
    latency_ms: int = 0
    created_at: datetime


class RunDetailResponse(BaseModel):
    """Detailed view of a run including its chronological event timeline."""

    run: RunResponse
    events: list[RunEventResponse] = Field(default_factory=list)


class PaginatedRunsResponse(BaseModel):
    """Paginated collection of runs."""

    items: list[RunResponse]
    total: int
    limit: int
    offset: int


# Place at the bottom of app/api/runs/schemas.py


class DecisionTraceItem(BaseModel):
    """Detailed trace step combining intent, policy verdict, and execution outcome."""

    id: UUID
    step_name: str
    action_type: str | None = None
    target: str | None = None
    capability: str | None = None
    decision: str  # ALLOW, DENY, REQUIRE_APPROVAL
    rule_matched: str | None = None
    risk_score: int = 0
    opa_query_id: str | None = None
    reason: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    execution_result: dict[str, Any] | None = None
    created_at: datetime


class RunDecisionTraceResponse(BaseModel):
    """Collection of decision traces for a single run."""

    run_id: UUID
    traces: list[DecisionTraceItem] = Field(default_factory=list)


class ProviderCostItem(BaseModel):
    """Token usage and USD cost for a specific provider/model."""

    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: Decimal = Decimal("0.000000")


class RunCostBreakdownResponse(BaseModel):
    """Comprehensive token and financial cost breakdown for a run."""

    run_id: UUID
    total_tokens: int
    total_cost_usd: Decimal
    providers: list[ProviderCostItem] = Field(default_factory=list)


class StatsSummaryResponse(BaseModel):
    """System-wide aggregate operational KPIs."""

    total_runs: int
    completed_runs: int
    failed_runs: int
    paused_runs: int
    success_rate_percent: float
    total_cost_usd: Decimal
    avg_duration_seconds: float
    pending_approvals: int
    total_tokens: int = 0


class ProviderHealthSnapshotResponse(BaseModel):
    """Live reliability and circuit status for an LLM provider."""

    provider: str
    model: str | None = None
    circuit_state: str  # CLOSED, OPEN, HALF_OPEN
    request_count: int
    error_count: int
    timeout_count: int
    avg_latency_ms: float
    last_updated: datetime


class HourlyVerificationOutcomeItem(BaseModel):
    """Hourly distribution of runs by outcome status."""

    time: str
    completed: int = 0
    paused: int = 0
    failed: int = 0
    active: bool = False


class ProviderCircuitActionResponse(BaseModel):
    """Response returned upon tripping or resetting a provider circuit."""

    provider: str
    circuit_state: str
    message: str
    updated_at: datetime


class CircuitTuningRequest(BaseModel):
    """Dynamic threshold parameters for circuit breaker orchestration."""

    consecutive_failures: int = Field(ge=1, le=10, default=3)
    probe_interval_seconds: int = Field(ge=10, le=300, default=60)
    recovery_threshold: int = Field(ge=1, le=10, default=5)


class CircuitTuningResponse(BaseModel):
    """Current active circuit breaker tuning thresholds."""

    consecutive_failures: int
    probe_interval_seconds: int
    recovery_threshold: int
    status: str = "applied"


class ProviderConfigItem(BaseModel):
    """Configuration metadata for an LLM provider and its active role."""

    name: str
    display_name: str
    models: list[str]
    selected_model: str
    role: str  # "primary", "fallback", "specialist"
    task_types: list[str]
    is_active: bool


class LLMProvidersConfigResponse(BaseModel):
    """Global multi-provider routing and active role configuration."""

    default_primary: str
    default_fallback: str
    routing_strategy: str
    providers: list[ProviderConfigItem]


class UpdateProviderRolesRequest(BaseModel):
    """Payload to dynamically modify primary/fallback roles, models, and task capabilities from the UI."""

    default_primary: str | None = None
    default_fallback: str | None = None
    routing_strategy: str | None = None
    provider_roles: dict[str, str] = Field(default_factory=dict)
    provider_models: dict[str, str] = Field(default_factory=dict)
    provider_task_types: dict[str, list[str]] = Field(default_factory=dict)


class UpdateProviderRolesResponse(BaseModel):
    """Confirmation returned after dynamically modifying provider roles."""

    success: bool
    message: str
    default_primary: str
    default_fallback: str
    providers: list[ProviderConfigItem]
