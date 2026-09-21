from __future__ import annotations

"""Unit tests for M2.9 Dynamic Budgets & Circuit Breakers (src/jarvis/kernel/circuit_breaker.py).

Verifies:
1. Sliding-window rate limiters for requests and tokens with sliding window pruning.
2. Hard budget ceilings (tokens and cost) per session and per mission (§80.4).
3. 4-state circuit breaker (CLOSED -> OPEN -> HALF_OPEN -> CLOSED / HOLD).
4. Automatic trip to HOLD under severe outages or error rates.
5. Invariant tests under simulated provider outages and token exhaustion.
"""

import pytest

from jarvis.kernel.circuit_breaker import (
    BudgetExceeded,
    CircuitBreaker,
    CircuitBreakerTripped,
    CircuitState,
    DynamicBudgetEnforcer,
    HoldTripped,
    ProviderGateLimiter,
    RateLimitExceeded,
    SlidingWindowRateLimiter,
)


class MockClock:
    """Deterministic monotonic clock for hermetic unit testing."""

    def __init__(self, initial_time: float = 1000.0) -> None:
        self._current_time = initial_time

    def __call__(self) -> float:
        return self._current_time

    def advance(self, seconds: float) -> None:
        self._current_time += seconds


# ---------------------------------------------------------------------------
# Sliding-Window Rate Limiter Tests
# ---------------------------------------------------------------------------

def test_rate_limiter_request_cap():
    clock = MockClock(100.0)
    limiter = SlidingWindowRateLimiter(
        max_requests=3,
        window_seconds=10.0,
        time_fn=clock,
    )

    # 3 allowed
    limiter.acquire("provider.a")
    limiter.acquire("provider.a")
    limiter.acquire("provider.a")

    # 4th rejected
    with pytest.raises(RateLimitExceeded) as exc_info:
        limiter.acquire("provider.a")
    assert exc_info.value.limit_type == "requests"
    assert exc_info.value.limit_value == 3
    assert exc_info.value.retry_after > 0

    # Advance clock past window
    clock.advance(11.0)
    # Now allowed again
    limiter.acquire("provider.a")
    assert limiter.current_requests() == 1


def test_rate_limiter_token_cap():
    clock = MockClock(100.0)
    limiter = SlidingWindowRateLimiter(
        max_tokens=1000,
        window_seconds=60.0,
        time_fn=clock,
    )

    limiter.acquire("provider.b", requests=1, tokens=600)
    assert limiter.current_tokens() == 600

    # Request requiring 500 more exceeds 1000 limit
    with pytest.raises(RateLimitExceeded) as exc_info:
        limiter.acquire("provider.b", requests=1, tokens=500)
    assert exc_info.value.limit_type == "tokens"
    assert exc_info.value.limit_value == 1000

    # Advancing half window does not expire
    clock.advance(30.0)
    with pytest.raises(RateLimitExceeded):
        limiter.acquire("provider.b", requests=1, tokens=500)

    # Advancing past 60s expires the 600 tokens
    clock.advance(31.0)
    limiter.acquire("provider.b", requests=1, tokens=500)
    assert limiter.current_tokens() == 500


# ---------------------------------------------------------------------------
# Dynamic Budget Enforcer Tests
# ---------------------------------------------------------------------------

def test_session_token_budget_enforcement():
    enforcer = DynamicBudgetEnforcer(max_session_tokens=10_000)

    # Within budget
    enforcer.check_budget(tokens=4000)
    enforcer.record_spend(tokens=4000)
    assert enforcer.session.spent_tokens == 4000

    enforcer.check_budget(tokens=5000)
    enforcer.record_spend(tokens=5000)
    assert enforcer.session.spent_tokens == 9000

    # 2000 more would exceed 10000
    with pytest.raises(BudgetExceeded) as exc_info:
        enforcer.check_budget(tokens=2000)
    assert exc_info.value.scope == "session"
    assert exc_info.value.metric == "tokens"
    assert exc_info.value.limit == 10_000
    assert exc_info.value.spent == 9000
    assert exc_info.value.requested == 2000


def test_session_cost_budget_enforcement():
    enforcer = DynamicBudgetEnforcer(max_session_cost=5.0)

    enforcer.check_budget(cost=3.5)
    enforcer.record_spend(cost=3.5)

    with pytest.raises(BudgetExceeded) as exc_info:
        enforcer.check_budget(cost=2.0)
    assert exc_info.value.metric == "cost"
    assert exc_info.value.limit == 5.0
    assert exc_info.value.spent == 3.5


def test_per_mission_budget_isolation():
    enforcer = DynamicBudgetEnforcer(
        max_session_tokens=50_000,
        default_mission_tokens=5_000,
    )

    enforcer.allocate_mission("mission-alpha", max_tokens=2_000)
    enforcer.allocate_mission("mission-beta", max_tokens=8_000)

    # Mission Alpha exceeds its 2000 limit
    enforcer.check_budget(tokens=1500, mission_id="mission-alpha")
    enforcer.record_spend(tokens=1500, mission_id="mission-alpha")

    with pytest.raises(BudgetExceeded) as exc_info:
        enforcer.check_budget(tokens=600, mission_id="mission-alpha")
    assert "mission 'mission-alpha'" in exc_info.value.scope

    # Mission Beta is completely independent and succeeds
    enforcer.check_budget(tokens=5000, mission_id="mission-beta")
    enforcer.record_spend(tokens=5000, mission_id="mission-beta")
    assert enforcer.get_mission_slab("mission-beta").spent_tokens == 5000


# ---------------------------------------------------------------------------
# Circuit Breaker Lifecycle & State Transitions
# ---------------------------------------------------------------------------

def test_circuit_breaker_normal_closed_operation():
    clock = MockClock(100.0)
    breaker = CircuitBreaker("model.primary", time_fn=clock)

    assert breaker.state == CircuitState.CLOSED
    assert breaker.allow_request() is True
    breaker.check_request()

    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.consecutive_failures == 0


def test_circuit_breaker_trips_to_open_on_consecutive_failures():
    clock = MockClock(100.0)
    breaker = CircuitBreaker(
        "model.primary",
        failure_threshold=3,
        recovery_timeout_seconds=20.0,
        time_fn=clock,
    )

    breaker.record_failure("error 1")
    breaker.record_failure("error 2")
    assert breaker.state == CircuitState.CLOSED

    # 3rd failure trips to OPEN
    breaker.record_failure("error 3")
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False

    with pytest.raises(CircuitBreakerTripped) as exc_info:
        breaker.check_request()
    assert exc_info.value.state == CircuitState.OPEN
    assert exc_info.value.retry_after > 0


def test_circuit_breaker_half_open_recovery():
    clock = MockClock(100.0)
    breaker = CircuitBreaker(
        "model.primary",
        failure_threshold=2,
        recovery_timeout_seconds=10.0,
        consecutive_success_threshold=2,
        time_fn=clock,
    )

    breaker.record_failure("fail 1")
    breaker.record_failure("fail 2")
    assert breaker.state == CircuitState.OPEN

    # Advance clock past recovery timeout (10s)
    clock.advance(11.0)
    assert breaker.check_state() == CircuitState.HALF_OPEN
    assert breaker.allow_request() is True

    # 1st success in HALF_OPEN
    breaker.record_success()
    assert breaker.state == CircuitState.HALF_OPEN

    # 2nd success recovers circuit to CLOSED
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.consecutive_failures == 0


def test_circuit_breaker_half_open_failure_returns_to_open():
    clock = MockClock(100.0)
    breaker = CircuitBreaker(
        "model.primary",
        failure_threshold=2,
        recovery_timeout_seconds=10.0,
        time_fn=clock,
    )

    breaker.record_failure("fail 1")
    breaker.record_failure("fail 2")
    assert breaker.state == CircuitState.OPEN

    clock.advance(15.0)
    assert breaker.check_state() == CircuitState.HALF_OPEN

    # Failure during probing immediately returns to OPEN
    breaker.record_failure("probe failed")
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False


def test_circuit_breaker_error_rate_trip():
    clock = MockClock(100.0)
    breaker = CircuitBreaker(
        "model.primary",
        failure_threshold=10,  # high consecutive threshold
        error_rate_threshold=0.5,  # 50% error rate
        min_samples_for_rate=4,
        window_seconds=60.0,
        time_fn=clock,
    )

    # 2 successes, 2 failures -> 50% error rate
    breaker.record_success()
    breaker.record_failure("err1")
    breaker.record_success()
    breaker.record_failure("err2")

    assert breaker.state == CircuitState.OPEN
    assert "error rate" in breaker.last_failure_reason.lower()


def test_circuit_breaker_automatic_trip_to_hold():
    clock = MockClock(100.0)
    breaker = CircuitBreaker(
        "model.primary",
        failure_threshold=3,
        hold_threshold=6,
        recovery_timeout_seconds=5.0,
        time_fn=clock,
    )

    # 3 failures -> OPEN
    for i in range(3):
        breaker.record_failure(f"err {i}")
    assert breaker.state == CircuitState.OPEN

    # Advance to HALF_OPEN and fail again
    clock.advance(6.0)
    breaker.record_failure("err 3")
    clock.advance(6.0)
    breaker.record_failure("err 4")
    clock.advance(6.0)
    breaker.record_failure("err 5")  # 6th failure -> HOLD

    assert breaker.state == CircuitState.HOLD

    # In HOLD, advancing time NEVER recovers
    clock.advance(1000.0)
    assert breaker.check_state() == CircuitState.HOLD

    with pytest.raises(HoldTripped):
        breaker.check_request()


def test_circuit_breaker_manual_hold_and_reset():
    breaker = CircuitBreaker("model.test")
    breaker.trip_hold("operator manual intervention")
    assert breaker.state == CircuitState.HOLD

    with pytest.raises(HoldTripped) as exc_info:
        breaker.check_request()
    assert "operator manual intervention" in str(exc_info.value)

    # Reset clears HOLD back to CLOSED
    breaker.reset()
    assert breaker.state == CircuitState.CLOSED
    breaker.check_request()


# ---------------------------------------------------------------------------
# Integrated Provider Gate Limiter Tests
# ---------------------------------------------------------------------------

def test_provider_gate_limiter_lifecycle():
    clock = MockClock(100.0)
    enforcer = DynamicBudgetEnforcer(max_session_tokens=10_000)
    gate = ProviderGateLimiter(
        budget_enforcer=enforcer,
        default_rate_requests=10,
        default_rate_tokens=5_000,
        failure_threshold=3,
        time_fn=clock,
    )

    # Successful call
    gate.before_call("model.claude", mission_id="m-1", estimated_tokens=100)
    gate.on_success("model.claude", mission_id="m-1", actual_tokens=100, actual_cost=0.01)

    assert enforcer.session.spent_tokens == 100

    # Simulated provider outage: 3 failures
    for i in range(3):
        gate.before_call("model.claude", mission_id="m-1", estimated_tokens=100)
        gate.on_failure("model.claude", reason=f"500 Internal Server Error #{i}")

    # Circuit is now OPEN: next call blocked pre-flight
    with pytest.raises(CircuitBreakerTripped):
        gate.before_call("model.claude", mission_id="m-1", estimated_tokens=100)


def test_provider_gate_limiter_token_exhaustion():
    clock = MockClock(100.0)
    enforcer = DynamicBudgetEnforcer(max_session_tokens=500)
    gate = ProviderGateLimiter(
        budget_enforcer=enforcer,
        time_fn=clock,
    )

    gate.before_call("model.gpt", estimated_tokens=400)
    gate.on_success("model.gpt", actual_tokens=400)

    # Next call requiring 200 exceeds 500 budget
    with pytest.raises(BudgetExceeded):
        gate.before_call("model.gpt", estimated_tokens=200)
