"""
Unit tests for CircuitBreaker state machine and concurrency guarantees.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.exceptions import LLMCircuitBreakerOpenError
from app.domain.models.provider_health import CircuitState
from app.infrastructure.llm.circuit_breaker import CircuitBreaker


@pytest.mark.asyncio
async def test_circuit_breaker_starts_closed() -> None:
    breaker = CircuitBreaker(provider_name="gemini")
    assert breaker.state == CircuitState.CLOSED
    assert await breaker.can_execute() is True


@pytest.mark.asyncio
async def test_circuit_breaker_trips_to_open_on_high_error_rate() -> None:
    breaker = CircuitBreaker(
        provider_name="gemini",
        failure_threshold=0.5,
        min_requests_in_window=4,
    )

    # 2 successes, 2 failures -> 50% failure rate with 4 requests
    await breaker.record_success()
    await breaker.record_success()
    await breaker.record_failure()
    await breaker.record_failure()

    assert breaker.state == CircuitState.OPEN
    assert await breaker.can_execute() is False

    with pytest.raises(LLMCircuitBreakerOpenError):
        await breaker.ensure_available()


@pytest.mark.asyncio
async def test_recovery_transition_to_half_open_after_cooldown() -> None:
    breaker = CircuitBreaker(
        provider_name="gemini",
        recovery_time_seconds=10,
    )
    breaker._state = CircuitState.OPEN
    # Simulate that recovery cooldown elapsed 11 seconds ago
    breaker._last_state_change = datetime.now(UTC) - timedelta(seconds=11)

    # First request should transition to HALF_OPEN and claim the probe ticket
    can_run = await breaker.can_execute()
    assert can_run is True
    assert breaker.state == CircuitState.HALF_OPEN
    assert breaker.is_probe_in_flight is True


@pytest.mark.asyncio
async def test_half_open_blocks_concurrent_thundering_herd() -> None:
    """
    Validates that when in HALF_OPEN, exactly 1 request gets the probe ticket
    and 99 concurrent requests are blocked.
    """
    breaker = CircuitBreaker(
        provider_name="gemini",
        recovery_time_seconds=10,
    )
    breaker._state = CircuitState.OPEN
    breaker._last_state_change = datetime.now(UTC) - timedelta(seconds=15)

    # 100 concurrent requests arriving at the same time
    results = await asyncio.gather(*(breaker.can_execute() for _ in range(100)))

    # Exactly 1 request gets True (the scout), 99 get False (redirect to fallback)
    assert results.count(True) == 1
    assert results.count(False) == 99
    assert breaker.state == CircuitState.HALF_OPEN
    assert breaker.is_probe_in_flight is True


@pytest.mark.asyncio
async def test_half_open_probe_success_resets_to_closed() -> None:
    breaker = CircuitBreaker(provider_name="gemini")
    breaker._state = CircuitState.HALF_OPEN
    breaker._probe_in_flight = True

    await breaker.record_success()

    assert breaker.state == CircuitState.CLOSED
    assert breaker.is_probe_in_flight is False
    assert await breaker.can_execute() is True


@pytest.mark.asyncio
async def test_half_open_probe_failure_trips_back_to_open() -> None:
    breaker = CircuitBreaker(provider_name="gemini")
    breaker._state = CircuitState.HALF_OPEN
    breaker._probe_in_flight = True

    await breaker.record_failure()

    assert breaker.state == CircuitState.OPEN
    assert breaker.is_probe_in_flight is False
    assert await breaker.can_execute() is False
