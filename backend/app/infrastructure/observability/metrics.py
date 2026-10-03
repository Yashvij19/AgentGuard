"""
OpenTelemetry Metrics instruments for AgentGuard runs, token economics, and policy risk.
"""

from typing import Any

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource

from app.config import Settings

_meter_provider: MeterProvider | None = None

# Metrics Instruments
runs_counter: Any = None
runs_duration_histogram: Any = None
llm_tokens_counter: Any = None
llm_cost_counter: Any = None
llm_latency_histogram: Any = None
llm_circuit_trips_counter: Any = None
policy_decisions_counter: Any = None
policy_risk_histogram: Any = None


def init_metrics(settings: Settings) -> MeterProvider:
    """Initialize OpenTelemetry MeterProvider and operational instruments."""
    global _meter_provider, runs_counter, runs_duration_histogram
    global llm_tokens_counter, llm_cost_counter, llm_latency_histogram
    global llm_circuit_trips_counter, policy_decisions_counter, policy_risk_histogram

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.app_env.value,
        }
    )

    provider = MeterProvider(resource=resource)
    metrics.set_meter_provider(provider)
    _meter_provider = provider

    meter = metrics.get_meter("agentguard.metrics")

    # Run Instruments
    runs_counter = meter.create_counter(
        name="agentguard.runs.total",
        description="Total number of agent runs executed",
        unit="1",
    )
    runs_duration_histogram = meter.create_histogram(
        name="agentguard.runs.duration_seconds",
        description="Execution duration of agent runs in seconds",
        unit="s",
    )

    # LLM & Cost Instruments
    llm_tokens_counter = meter.create_counter(
        name="agentguard.llm.tokens_total",
        description="Total tokens consumed by LLM providers",
        unit="1",
    )
    llm_cost_counter = meter.create_counter(
        name="agentguard.llm.cost_usd",
        description="Estimated financial cost in USD for LLM inference",
        unit="USD",
    )
    llm_latency_histogram = meter.create_histogram(
        name="agentguard.llm.latency_seconds",
        description="Inference round-trip latency of LLM providers",
        unit="s",
    )
    llm_circuit_trips_counter = meter.create_counter(
        name="agentguard.llm.circuit_breaker_trips",
        description="Count of circuit breaker trips to OPEN per provider",
        unit="1",
    )

    # Governance & Policy Instruments
    policy_decisions_counter = meter.create_counter(
        name="agentguard.policy.decisions_total",
        description="Count of policy decisions emitted (ALLOW, DENY, REQUIRE_APPROVAL)",
        unit="1",
    )
    policy_risk_histogram = meter.create_histogram(
        name="agentguard.policy.risk_score",
        description="Distribution of calculated risk scores for actions",
        unit="1",
    )

    return provider


def record_run_completion(status: str, duration_sec: float) -> None:
    """Record run completion counters and duration histogram."""
    if runs_counter:
        runs_counter.add(1, {"status": status})
    if runs_duration_histogram:
        runs_duration_histogram.record(duration_sec, {"status": status})


def record_llm_usage(
    provider: str,
    model: str,
    tokens: int,
    cost_usd: float,
    latency_sec: float,
) -> None:
    """Record LLM token consumption, cost, and latency."""
    if llm_tokens_counter:
        llm_tokens_counter.add(tokens, {"gen_ai.system": provider, "gen_ai.request.model": model})
    if llm_cost_counter:
        llm_cost_counter.add(cost_usd, {"gen_ai.system": provider})
    if llm_latency_histogram:
        llm_latency_histogram.record(
            latency_sec, {"gen_ai.system": provider, "gen_ai.request.model": model}
        )


def record_policy_verdict(decision: str, risk_score: int) -> None:
    """Record policy decision type and risk score."""
    if policy_decisions_counter:
        policy_decisions_counter.add(1, {"decision": decision})
    if policy_risk_histogram:
        policy_risk_histogram.record(risk_score)
