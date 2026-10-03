"""
OpenTelemetry Tracing setup with GenAI Semantic Conventions support.
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Tracer

from app.config import Settings

# Standard GenAI & Governance Semantic Conventions attributes
GEN_AI_SYSTEM = "gen_ai.system"
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
GEN_AI_USAGE_TOTAL_TOKENS = "gen_ai.usage.total_tokens"

POLICY_DECISION = "policy.decision"
POLICY_RULE_MATCHED = "policy.rule_matched"
POLICY_RISK_SCORE = "policy.risk_score"

TOOL_CAPABILITY = "tool.capability"
SANDBOX_PROVIDER = "sandbox.provider"

_tracer_provider: TracerProvider | None = None


def init_tracing(settings: Settings) -> TracerProvider:
    """
    Initialize global OpenTelemetry TracerProvider.
    Connects to OTLP HTTP endpoint (e.g. Grafana Cloud) if configured;
    otherwise runs in-memory/no-op for local development and testing.
    """
    global _tracer_provider

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.app_env.value,
            "service.version": "0.1.0",
        }
    )

    provider = TracerProvider(resource=resource)

    if settings.otel_exporter_otlp_endpoint:
        headers = {}
        if settings.otel_exporter_otlp_headers:
            for pair in settings.otel_exporter_otlp_headers.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    headers[k.strip()] = v.strip()

        otlp_exporter = OTLPSpanExporter(
            endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/traces",
            headers=headers,
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    trace.set_tracer_provider(provider)
    _tracer_provider = provider
    return provider


def get_tracer(name: str = "agentguard") -> Tracer:
    """Obtain a named OpenTelemetry tracer."""
    return trace.get_tracer(name)


@contextmanager
def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> Generator[trace.Span, None, None]:
    """
    Convenient context manager for creating and automatically closing spans.
    Safely ignores errors if tracing is disabled.
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, val in attributes.items():
                if val is not None:
                    span.set_attribute(key, val)
        yield span


def shutdown_tracing() -> None:
    """Flush and shut down active tracer provider on application exit."""
    global _tracer_provider
    if _tracer_provider:
        _tracer_provider.shutdown()
        _tracer_provider = None
