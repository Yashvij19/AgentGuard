"""
Domain models for LLM provider health monitoring and circuit breaker tracking.
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CircuitState(StrEnum):
    """Three-state machine states for circuit breakers."""
    CLOSED = "closed"        # Healthy: Normal operations permitted
    OPEN = "open"            # Failing: Traffic halted, routed to fallback
    HALF_OPEN = "half_open"  # Recovery probe: Testing canary requests


class ProviderHealth(BaseModel):
    """
    Snapshot of provider reliability metrics within a sliding time window.
    Persisted to database to power observability dashboards.
    """
    id: UUID = Field(default_factory=uuid4)
    provider: str
    model: str
    window_start: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    timeout_count: int = Field(default=0, ge=0)
    avg_latency_ms: float = Field(default=0.0, ge=0.0)
    circuit_state: CircuitState = CircuitState.CLOSED

    @property
    def error_rate(self) -> float:
        """Calculate error ratio over total requests in current window."""
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count
