"""In-process circuit breaker for LLM provider calls (design §4.1).

Prevents cascading failures when a provider is down: after
``failure_threshold`` consecutive failures the breaker trips open and every
call fails fast (as :class:`LLMProviderError`) for ``reset_seconds`` before
allowing a single trial call through (half-open) to test recovery.

Deliberately in-process rather than Redis-backed: a breaker is a per-replica
performance safeguard, not a correctness mechanism, so there is no need to
coordinate state across replicas (design §10.1 "stateless by design").
"""

from __future__ import annotations

import time
from enum import Enum

from app.core.errors import LLMProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)


class _State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Tracks consecutive failures for one provider and short-circuits calls
    while it is judged unhealthy."""

    def __init__(self, *, failure_threshold: int, reset_seconds: float, name: str) -> None:
        self._failure_threshold = failure_threshold
        self._reset_seconds = reset_seconds
        self._name = name
        self._state = _State.CLOSED
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    def before_call(self) -> None:
        """Raise if the breaker is open and the reset window has not elapsed."""
        if self._state is _State.OPEN:
            assert self._opened_at is not None
            if time.monotonic() - self._opened_at < self._reset_seconds:
                raise LLMProviderError(
                    f"The {self._name} provider is temporarily unavailable (circuit breaker open)."
                )
            self._state = _State.HALF_OPEN
            logger.info(
                "llm.circuit_breaker.half_open",
                extra={"event": "llm.circuit_breaker.half_open", "provider": self._name},
            )

    def on_success(self) -> None:
        if self._state is not _State.CLOSED:
            logger.info(
                "llm.circuit_breaker.closed",
                extra={"event": "llm.circuit_breaker.closed", "provider": self._name},
            )
        self._state = _State.CLOSED
        self._consecutive_failures = 0
        self._opened_at = None

    def on_failure(self) -> None:
        self._consecutive_failures += 1
        if self._state is _State.HALF_OPEN or self._consecutive_failures >= self._failure_threshold:
            self._state = _State.OPEN
            self._opened_at = time.monotonic()
            logger.warning(
                "llm.circuit_breaker.open",
                extra={
                    "event": "llm.circuit_breaker.open",
                    "provider": self._name,
                    "consecutive_failures": self._consecutive_failures,
                },
            )
