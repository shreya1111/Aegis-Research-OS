"""Unit tests for the LLM provider circuit breaker (design §4.1)."""

from __future__ import annotations

import time

import pytest

from app.core.errors import LLMProviderError
from app.core.llm.circuit_breaker import CircuitBreaker


@pytest.mark.unit
def test_breaker_stays_closed_below_the_failure_threshold() -> None:
    breaker = CircuitBreaker(failure_threshold=3, reset_seconds=30, name="test")

    breaker.on_failure()
    breaker.on_failure()

    breaker.before_call()  # must not raise


@pytest.mark.unit
def test_breaker_opens_at_the_failure_threshold() -> None:
    breaker = CircuitBreaker(failure_threshold=3, reset_seconds=30, name="test")

    for _ in range(3):
        breaker.on_failure()

    with pytest.raises(LLMProviderError):
        breaker.before_call()


@pytest.mark.unit
def test_breaker_resets_the_failure_count_on_success() -> None:
    breaker = CircuitBreaker(failure_threshold=3, reset_seconds=30, name="test")

    breaker.on_failure()
    breaker.on_failure()
    breaker.on_success()
    breaker.on_failure()
    breaker.on_failure()

    breaker.before_call()  # still below threshold after the reset


@pytest.mark.unit
def test_breaker_allows_a_trial_call_after_the_reset_window_elapses() -> None:
    breaker = CircuitBreaker(failure_threshold=1, reset_seconds=0.01, name="test")

    breaker.on_failure()
    with pytest.raises(LLMProviderError):
        breaker.before_call()

    time.sleep(0.02)

    breaker.before_call()  # half-open: the trial call is allowed through


@pytest.mark.unit
def test_a_failure_during_the_half_open_trial_reopens_the_breaker() -> None:
    breaker = CircuitBreaker(failure_threshold=1, reset_seconds=0.01, name="test")

    breaker.on_failure()
    time.sleep(0.02)
    breaker.before_call()  # now half-open
    breaker.on_failure()

    with pytest.raises(LLMProviderError):
        breaker.before_call()
