"""
Circuit breaker implementation for multi-provider resilience.
Enforces fail-fast behavior on unhealthy providers with atomic single-probe canary testing.
"""

import asyncio
from collections import deque
from datetime import UTC, datetime

from app.domain.exceptions import LLMCircuitBreakerOpenError
from app.domain.models.provider_health import CircuitState


class CircuitBreaker:
    """
    Per-provider circuit breaker state machine.
    Tracks error rates across a sliding time window and governs state transitions:
    CLOSED -> OPEN -> HALF_OPEN -> CLOSED.

    In HALF_OPEN state, strictly enforces a single-probe canary policy:
    only ONE in-flight request is permitted to probe the upstream service.
    All concurrent requests are immediately rejected to protect the recovering provider.
    """

    def __init__(
        self,
        provider_name: str,
        failure_threshold: float = 0.5,
        recovery_time_seconds: int = 60,
        window_seconds: int = 300,
        min_requests_in_window: int = 4,
        probe_timeout_seconds: int = 30,
    ) -> None:
        self.provider_name = provider_name
        self.failure_threshold = failure_threshold
        self.recovery_time_seconds = recovery_time_seconds
        self.window_seconds = window_seconds
        self.min_requests_in_window = min_requests_in_window
        self.probe_timeout_seconds = probe_timeout_seconds

        self._state: CircuitState = CircuitState.CLOSED
        self._last_state_change: datetime = datetime.now(UTC)

        # Single-probe canary concurrency guard
        self._probe_in_flight: bool = False
        self._probe_started_at: datetime | None = None
        self._window: deque[tuple[float, bool]] = deque()
        # Sliding window stores tuples: (timestamp_float, is_error_bool)

        self._lock: asyncio.Lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def is_probe_in_flight(self) -> bool:
        return self._probe_in_flight

    def _purge_stale_entries(self, current_time: float) -> None:
        """Remove entries outside the active sliding window."""
        cutoff = current_time - self.window_seconds
        while self._window and self._window[0][0] < cutoff:
            self._window.popleft()

    async def can_execute(self) -> bool:
        """
        Check whether a request is permitted through the circuit breaker.
        Enforces strict single-probe gating during HALF_OPEN recovery.
        """
        async with self._lock:
            now = datetime.now(UTC)
            now_ts = now.timestamp()
            self._purge_stale_entries(now_ts)

            # 1. CLOSED: Healthy provider, all traffic permitted
            if self._state == CircuitState.CLOSED:
                return True

            # 2. OPEN: Tripped provider, check if recovery cooldown elapsed
            if self._state == CircuitState.OPEN:
                elapsed = (now - self._last_state_change).total_seconds()
                if elapsed >= self.recovery_time_seconds:
                    # Transition to HALF_OPEN and atomically claim the single probe ticket
                    self._state = CircuitState.HALF_OPEN
                    self._last_state_change = now
                    self._probe_in_flight = True
                    self._probe_started_at = now
                    return True
                return False

            # 3. HALF_OPEN: Recovery probe mode
            if self._state == CircuitState.HALF_OPEN:
                # If no probe is currently running, grant the ticket
                if not self._probe_in_flight:
                    self._probe_in_flight = True
                    self._probe_started_at = now
                    return True

                # Check failsafe: if probe has hung longer than probe_timeout_seconds,
                # assume the previous coroutine died/hung and grant a fresh probe ticket.
                if self._probe_started_at is not None:
                    probe_duration = (now - self._probe_started_at).total_seconds()
                    if probe_duration >= self.probe_timeout_seconds:
                        self._probe_started_at = now
                        return True

                # A canary probe is actively in-flight. Disallow concurrent callers!
                return False

            return False

    async def record_success(self) -> None:
        """
        Record a successful completion.
        If in HALF_OPEN state, this successful canary resets the breaker to CLOSED.
        """
        async with self._lock:
            now = datetime.now(UTC)
            now_ts = now.timestamp()
            self._purge_stale_entries(now_ts)

            if self._state == CircuitState.HALF_OPEN:
                # Canary probe succeeded! Re-close the circuit and clear error history.
                self._state = CircuitState.CLOSED
                self._last_state_change = now
                self._probe_in_flight = False
                self._probe_started_at = None
                self._window.clear()
            else:
                self._window.append((now_ts, False))

    async def record_failure(self) -> None:
        """
        Record a failed call (timeout, 5xx, or 429).
        Trips breaker to OPEN if error rate exceeds failure_threshold.
        If in HALF_OPEN, immediately trips back to OPEN and resets cooldown.
        """
        async with self._lock:
            now = datetime.now(UTC)
            now_ts = now.timestamp()
            self._purge_stale_entries(now_ts)

            if self._state == CircuitState.HALF_OPEN:
                # Canary probe failed: immediately re-trip to OPEN and restart cooldown
                self._state = CircuitState.OPEN
                self._last_state_change = now
                self._probe_in_flight = False
                self._probe_started_at = None
                self._window.append((now_ts, True))
                return

            self._window.append((now_ts, True))
            total_requests = len(self._window)
            error_count = sum(1 for _, is_error in self._window if is_error)

            if total_requests >= self.min_requests_in_window:
                error_rate = error_count / total_requests
                if error_rate >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._last_state_change = now

    async def ensure_available(self) -> None:
        """
        Convenience guard: raises LLMCircuitBreakerOpenError if circuit is not permitting calls.
        """
        if not await self.can_execute():
            raise LLMCircuitBreakerOpenError(
                f"Circuit breaker for provider '{self.provider_name}' is not accepting traffic "
                f"(state={self._state.value}). Request routed to fallback."
            )
