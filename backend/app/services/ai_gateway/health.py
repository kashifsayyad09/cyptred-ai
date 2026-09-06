"""
Provider health tracker.

Tracks consecutive failures and successes so the gateway can:
  - switch to FALLBACK after repeated Groq failures
  - restore PRIMARY (Groq) automatically when it becomes healthy again

Thread-safety: asyncio.Lock — safe for use in a single-process async server.
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum


class HealthState(str, Enum):
    HEALTHY  = "healthy"
    DEGRADED = "degraded"    # some failures, but still being tried
    UNHEALTHY = "unhealthy"  # circuit open — not being tried


class ProviderHealth:
    """
    Per-provider health state machine.

    States:
        HEALTHY   → consecutive_failures < failure_threshold
        DEGRADED  → failure_threshold <= consecutive_failures < open_threshold
        UNHEALTHY → consecutive_failures >= open_threshold (circuit open)

    Recovery: after recovery_threshold consecutive successes → HEALTHY
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 2,
        open_threshold: int = 3,
        recovery_threshold: int = 3,
    ) -> None:
        self.name = name
        self._failure_threshold = failure_threshold
        self._open_threshold = open_threshold
        self._recovery_threshold = recovery_threshold

        self._consecutive_failures: int = 0
        self._consecutive_successes: int = 0
        self._state: HealthState = HealthState.HEALTHY
        self._last_failure_at: float | None = None
        self._last_success_at: float | None = None
        self._total_requests: int = 0
        self._total_failures: int = 0
        self._lock = asyncio.Lock()

    # ── Public interface ──────────────────────────────────────────────────────

    @property
    def state(self) -> HealthState:
        return self._state

    @property
    def is_available(self) -> bool:
        """Return True when the provider should be tried."""
        return self._state != HealthState.UNHEALTHY

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    @property
    def consecutive_successes(self) -> int:
        return self._consecutive_successes

    async def record_success(self) -> None:
        async with self._lock:
            self._total_requests += 1
            self._consecutive_failures = 0
            self._consecutive_successes += 1
            self._last_success_at = time.time()
            if self._consecutive_successes >= self._recovery_threshold:
                self._state = HealthState.HEALTHY

    async def record_failure(self) -> None:
        async with self._lock:
            self._total_requests += 1
            self._total_failures += 1
            self._consecutive_failures += 1
            self._consecutive_successes = 0
            self._last_failure_at = time.time()
            if self._consecutive_failures >= self._open_threshold:
                self._state = HealthState.UNHEALTHY
            elif self._consecutive_failures >= self._failure_threshold:
                self._state = HealthState.DEGRADED

    def reset(self) -> None:
        """Hard reset — used in tests."""
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._state = HealthState.HEALTHY

    def to_dict(self) -> dict:
        return {
            "provider":              self.name,
            "state":                 self._state.value,
            "consecutive_failures":  self._consecutive_failures,
            "consecutive_successes": self._consecutive_successes,
            "total_requests":        self._total_requests,
            "total_failures":        self._total_failures,
            "last_failure_at":       self._last_failure_at,
            "last_success_at":       self._last_success_at,
        }
