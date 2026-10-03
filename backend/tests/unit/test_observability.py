"""
Unit tests for OpenTelemetry tracing and metrics instruments.
"""

from app.config import Settings
from app.infrastructure.observability.metrics import (
    init_metrics,
    record_llm_usage,
    record_policy_verdict,
    record_run_completion,
)
from app.infrastructure.observability.tracing import (
    GEN_AI_REQUEST_MODEL,
    GEN_AI_SYSTEM,
    POLICY_DECISION,
    init_tracing,
    shutdown_tracing,
    trace_span,
)


def test_tracing_lifecycle_and_span_creation() -> None:
    """Verify TracerProvider initializes and records spans with attributes."""
    test_settings = Settings(
        database_url="postgresql+asyncpg://user:pass@localhost/db",
        github_app_id="123",
        github_webhook_secret="sec",
        github_private_key="key",
    )

    provider = init_tracing(test_settings)
    assert provider is not None

    # Test creating a span with GenAI attributes
    with trace_span(
        "gen_ai.gemini.call",
        attributes={
            GEN_AI_SYSTEM: "gemini",
            GEN_AI_REQUEST_MODEL: "gemini-2.0-flash",
            POLICY_DECISION: "ALLOW",
        },
    ) as span:
        assert span.is_recording() is True

    shutdown_tracing()


def test_metrics_instruments_recording() -> None:
    """Verify metrics instruments record without errors."""
    test_settings = Settings(
        database_url="postgresql+asyncpg://user:pass@localhost/db",
        github_app_id="123",
        github_webhook_secret="sec",
        github_private_key="key",
    )

    init_metrics(test_settings)

    # Record test metrics
    record_run_completion(status="completed", duration_sec=14.5)
    record_llm_usage(
        provider="groq",
        model="llama-3.3-70b",
        tokens=1200,
        cost_usd=0.012,
        latency_sec=0.45,
    )
    record_policy_verdict(decision="REQUIRE_APPROVAL", risk_score=85)
