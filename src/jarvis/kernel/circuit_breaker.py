from __future__ import annotations

"""Dynamic Budgets & Circuit Breakers (Milestone M2.9, spec §80.4 / §119 / §131.6–131.7).

Provides:
1. Sliding-window rate limiters (`SlidingWindowRateLimiter`) for external model
   and API providers, tracking request and token throughput over configurable time windows.
2. Dynamic budget enforcement (`DynamicBudgetEnforcer`): hard token and cost ceilings
   per session and per mission (§80.4), preventing runaway resource consumption.
3. Provider circuit breakers (`CircuitBreaker`): 4-state state machine (CLOSED, OPEN,
   HALF_OPEN, HOLD) with automatic trip to HOLD when error rates or consecutive
   failures exceed thresholds (§119).
4. Unified provider gate limiter (`ProviderGateLimiter`): combines rate limiting,
   circuit breaking, and budget enforcement before dispatching to external providers.

Invariants:
1. Hermetic & Deterministic by Default: Clock access is injected via `time_fn` (defaults
   to `time.time`). In tests, a deterministic monotonic clock is injected without sleep.
2. Fail-Closed on Budget: Hard token and cost ceilings are non-negotiable. If an operation
   would exceed the session or mission ceiling, it is blocked with `BudgetExceeded`.
3. Circuit Breaker Priority (§119, §131.7 #8): Every external provider is protected by a
   circuit breaker. Tripped breakers fail fast with `CircuitBreakerTripped` without invoking
   external network calls.
4. Automatic Trip to HOLD: Repeated outages or extreme error rates trip the breaker to `HOLD`,
   halting further attempts until explicitly reset or cleared by an operator/creator.
5. Strictly Additive: Does not modify frozen kernel modules (modules 1–17 remain byte-identical).
"""

import collections
import enum
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CircuitBreakerError(RuntimeError):
    """Base exception for all circuit breaker, rate limit, and budget errors."""


class RateLimitExceeded(CircuitBreakerError):
    """Raised when an external provider rate limit (requests or tokens) is exceeded."""

    def __init__(
        self,
        provider_id: str,
        *,
        limit_type: str,
        limit_value: int | float,
        current_value: int | float,
        retry_after: float,
    ) -> None:
        super().__init__(
            f"Rate limit exceeded for provider '{provider_id}': {limit_type} "
            f"limit is {limit_value}, currently at {current_value}. Retry after {retry_after:.2f}s"
        )
        self.provider_id = provider_id
        self.limit_type = limit_type
        self.limit_value = limit_value
        self.current_value = current_value
        self.retry_after = retry_after


class BudgetExceeded(CircuitBreakerError):
    """Raised when a session or mission hard budget ceiling is reached."""

    def __init__(
        self,
        scope: str,
        *,
        metric: str,
        limit: float,
        spent: float,
        requested: float,
    ) -> None:
        super().__init__(
            f"Hard budget ceiling exceeded for {scope}: {metric} limit is {limit}, "
            f"already spent {spent}, requested {requested} (total {spent + requested})"
        )
        self.scope = scope
        self.metric = metric
        self.limit = limit
        self.spent = spent
        self.requested = requested


class CircuitBreakerTripped(CircuitBreakerError):
    """Raised when a call is attempted against a tripped (OPEN or HOLD) circuit breaker."""

    def __init__(
        self,
        provider_id: str,
        *,
        state: "CircuitState",
        reason: str,
        retry_after: float | None = None,
    ) -> None:
        msg = f"Circuit breaker for provider '{provider_id}' is {state.value.upper()}: {reason}"
        if retry_after is not None and retry_after > 0:
            msg += f" (retry after {retry_after:.2f}s)"
        super().__init__(msg)
        self.provider_id = provider_id
        self.state = state
        self.reason = reason
        self.retry_after = retry_after


class HoldTripped(CircuitBreakerTripped):
    """Raised specifically when a circuit breaker has entered the unrecoverable HOLD state."""

    def __init__(self, provider_id: str, *, reason: str) -> None:
        super().__init__(
            provider_id,
            state=CircuitState.HOLD,
            reason=f"Permanently held due to severe failure: {reason}",
            retry_after=None,
        )


# ---------------------------------------------------------------------------
# Circuit States
# ---------------------------------------------------------------------------

class CircuitState(str, enum.Enum):
    """Operational states of a provider circuit breaker."""

    CLOSED = "closed"        # Normal operation: calls pass through
    OPEN = "open"            # Tripped: calls fail fast until recovery timeout
    HALF_OPEN = "half_open"  # Probing: limited test calls allowed to check recovery
    HOLD = "hold"            # Unrecoverable trip: requires operator/creator intervention


# ---------------------------------------------------------------------------
# Sliding-Window Rate Limiter
# ---------------------------------------------------------------------------

@dataclass
class _RateTimestamp:
    ts: float
    count: int
    tokens: int


class SlidingWindowRateLimiter:
    """Sliding-window rate limiter tracking requests and tokens over a window.

    Maintains a deque of timestamped request entries. Entries older than
    `now - window_seconds` are pruned during evaluation.
    """

    def __init__(
        self,
        *,
        max_requests: int | None = None,
        max_tokens: int | None = None,
        window_seconds: float = 60.0,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        self.max_requests = max_requests
        self.max_tokens = max_tokens
        self.window_seconds = window_seconds
        self._time_fn = time_fn
        self._entries: collections.deque[_RateTimestamp] = collections.deque()

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._entries and self._entries[0].ts <= cutoff:
            self._entries.popleft()

    def current_requests(self, now: float | None = None) -> int:
        n = now if now is not None else self._time_fn()
        self._prune(n)
        return sum(e.count for e in self._entries)

    def current_tokens(self, now: float | None = None) -> int:
        n = now if now is not None else self._time_fn()
        self._prune(n)
        return sum(e.tokens for e in self._entries)

    def check(
        self,
        requests: int = 1,
        tokens: int = 0,
        *,
        now: float | None = None,
    ) -> tuple[bool, float]:
        """Checks if `requests` and `tokens` can be accommodated.

        Returns (allowed: bool, retry_after: float).
        """
        n = now if now is not None else self._time_fn()
        self._prune(n)

        req_sum = sum(e.count for e in self._entries)
        tok_sum = sum(e.tokens for e in self._entries)

        if self.max_requests is not None and (req_sum + requests) > self.max_requests:
            oldest = self._entries[0].ts if self._entries else n
            retry_after = max(0.0, (oldest + self.window_seconds) - n)
            return False, retry_after

        if self.max_tokens is not None and (tok_sum + tokens) > self.max_tokens:
            oldest = self._entries[0].ts if self._entries else n
            retry_after = max(0.0, (oldest + self.window_seconds) - n)
            return False, retry_after

        return True, 0.0

    def acquire(
        self,
        provider_id: str,
        requests: int = 1,
        tokens: int = 0,
        *,
        now: float | None = None,
    ) -> None:
        """Acquires rate limit capacity or raises `RateLimitExceeded`."""
        n = now if now is not None else self._time_fn()
        allowed, retry_after = self.check(requests=requests, tokens=tokens, now=n)
        if not allowed:
            req_sum = sum(e.count for e in self._entries)
            tok_sum = sum(e.tokens for e in self._entries)
            if self.max_requests is not None and (req_sum + requests) > self.max_requests:
                raise RateLimitExceeded(
                    provider_id,
                    limit_type="requests",
                    limit_value=self.max_requests,
                    current_value=req_sum + requests,
                    retry_after=retry_after,
                )
            raise RateLimitExceeded(
                provider_id,
                limit_type="tokens",
                limit_value=self.max_tokens or 0,
                current_value=tok_sum + tokens,
                retry_after=retry_after,
            )

        self._entries.append(_RateTimestamp(ts=n, count=requests, tokens=tokens))


# ---------------------------------------------------------------------------
# Dynamic Budget Enforcer
# ---------------------------------------------------------------------------

@dataclass
class _BudgetSlab:
    spent_tokens: int = 0
    spent_cost: float = 0.0
    token_limit: int | None = None
    cost_limit: float | None = None


class DynamicBudgetEnforcer:
    """Dynamic budget enforcer tracking token and financial cost ceilings.

    Enforces hard ceilings:
    - Global / session ceiling: `max_session_tokens`, `max_session_cost`
    - Per-mission ceiling (§80.4): `max_mission_tokens`, `max_mission_cost`
    """

    def __init__(
        self,
        *,
        max_session_tokens: int | None = None,
        max_session_cost: float | None = None,
        default_mission_tokens: int | None = None,
        default_mission_cost: float | None = None,
    ) -> None:
        self.session = _BudgetSlab(
            token_limit=max_session_tokens,
            cost_limit=max_session_cost,
        )
        self.default_mission_tokens = default_mission_tokens
        self.default_mission_cost = default_mission_cost
        self._missions: dict[str, _BudgetSlab] = {}

    def allocate_mission(
        self,
        mission_id: str,
        *,
        max_tokens: int | None = None,
        max_cost: float | None = None,
    ) -> None:
        """Sets explicit resource allocation for a mission."""
        tok_limit = max_tokens if max_tokens is not None else self.default_mission_tokens
        c_limit = max_cost if max_cost is not None else self.default_mission_cost
        slab = self._missions.setdefault(mission_id, _BudgetSlab())
        slab.token_limit = tok_limit
        slab.cost_limit = c_limit

    def get_mission_slab(self, mission_id: str) -> _BudgetSlab:
        if mission_id not in self._missions:
            self._missions[mission_id] = _BudgetSlab(
                token_limit=self.default_mission_tokens,
                cost_limit=self.default_mission_cost,
            )
        return self._missions[mission_id]

    def check_budget(
        self,
        tokens: int = 0,
        cost: float = 0.0,
        *,
        mission_id: str | None = None,
    ) -> None:
        """Checks if spending `tokens` and `cost` would exceed session or mission limits.

        Raises `BudgetExceeded` immediately if any hard ceiling is reached.
        """
        # 1. Session check
        if self.session.token_limit is not None:
            if self.session.spent_tokens + tokens > self.session.token_limit:
                raise BudgetExceeded(
                    "session",
                    metric="tokens",
                    limit=self.session.token_limit,
                    spent=self.session.spent_tokens,
                    requested=tokens,
                )
        if self.session.cost_limit is not None:
            if self.session.spent_cost + cost > self.session.cost_limit:
                raise BudgetExceeded(
                    "session",
                    metric="cost",
                    limit=self.session.cost_limit,
                    spent=self.session.spent_cost,
                    requested=cost,
                )

        # 2. Mission check
        if mission_id is not None:
            m_slab = self.get_mission_slab(mission_id)
            if m_slab.token_limit is not None:
                if m_slab.spent_tokens + tokens > m_slab.token_limit:
                    raise BudgetExceeded(
                        f"mission '{mission_id}'",
                        metric="tokens",
                        limit=m_slab.token_limit,
                        spent=m_slab.spent_tokens,
                        requested=tokens,
                    )
            if m_slab.cost_limit is not None:
                if m_slab.spent_cost + cost > m_slab.cost_limit:
                    raise BudgetExceeded(
                        f"mission '{mission_id}'",
                        metric="cost",
                        limit=m_slab.cost_limit,
                        spent=m_slab.spent_cost,
                        requested=cost,
                    )

    def record_spend(
        self,
        tokens: int = 0,
        cost: float = 0.0,
        *,
        mission_id: str | None = None,
    ) -> None:
        """Records actual spent tokens and cost against session and mission budgets."""
        self.session.spent_tokens += tokens
        self.session.spent_cost += cost
        if mission_id is not None:
            m_slab = self.get_mission_slab(mission_id)
            m_slab.spent_tokens += tokens
            m_slab.spent_cost += cost


# ---------------------------------------------------------------------------
# Provider Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """4-State Circuit Breaker with Error Rate and HOLD Escalation.

    Transitions:
    - CLOSED -> OPEN: triggered when consecutive failures >= `failure_threshold`
      OR window error rate >= `error_rate_threshold` (with at least `min_samples_for_rate`).
    - OPEN -> HALF_OPEN: after `recovery_timeout_seconds` has elapsed.
    - HALF_OPEN -> CLOSED: after `consecutive_success_threshold` consecutive successes.
    - HALF_OPEN -> OPEN: any failure in HALF_OPEN immediately returns to OPEN.
    - ANY -> HOLD: triggered when total consecutive failures >= `hold_threshold`
      OR catastrophic error rate occurs. In HOLD, calls never recover automatically.
    """

    def __init__(
        self,
        provider_id: str,
        *,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        consecutive_success_threshold: int = 2,
        hold_threshold: int = 10,
        error_rate_threshold: float = 0.6,
        min_samples_for_rate: int = 5,
        window_seconds: float = 60.0,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        self.provider_id = provider_id
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.consecutive_success_threshold = consecutive_success_threshold
        self.hold_threshold = hold_threshold
        self.error_rate_threshold = error_rate_threshold
        self.min_samples_for_rate = min_samples_for_rate
        self.window_seconds = window_seconds
        self._time_fn = time_fn

        self.state: CircuitState = CircuitState.CLOSED
        self.consecutive_failures: int = 0
        self.consecutive_successes: int = 0
        self.opened_at: float | None = None
        self.last_failure_reason: str = ""

        # Rolling window history of (timestamp, is_success)
        self._history: collections.deque[tuple[float, bool]] = collections.deque()

    def _prune_history(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._history and self._history[0][0] <= cutoff:
            self._history.popleft()

    def error_rate(self, now: float | None = None) -> float:
        n = now if now is not None else self._time_fn()
        self._prune_history(n)
        if not self._history:
            return 0.0
        failures = sum(1 for _, success in self._history if not success)
        return failures / len(self._history)

    def check_state(self, now: float | None = None) -> CircuitState:
        """Inspects and updates circuit state based on time elapsed."""
        n = now if now is not None else self._time_fn()

        if self.state is CircuitState.HOLD:
            return CircuitState.HOLD

        if self.state is CircuitState.OPEN:
            if self.opened_at is not None and (n - self.opened_at) >= self.recovery_timeout_seconds:
                self.state = CircuitState.HALF_OPEN
                self.consecutive_successes = 0

        return self.state

    def allow_request(self, now: float | None = None) -> bool:
        """Returns True if a request is permitted, False if tripped."""
        state = self.check_state(now)
        return state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def check_request(self, now: float | None = None) -> None:
        """Raises `CircuitBreakerTripped` or `HoldTripped` if request is not allowed."""
        n = now if now is not None else self._time_fn()
        state = self.check_state(n)

        if state is CircuitState.HOLD:
            raise HoldTripped(self.provider_id, reason=self.last_failure_reason)

        if state is CircuitState.OPEN:
            retry_after = (
                max(0.0, (self.opened_at + self.recovery_timeout_seconds) - n)
                if self.opened_at is not None
                else self.recovery_timeout_seconds
            )
            raise CircuitBreakerTripped(
                self.provider_id,
                state=CircuitState.OPEN,
                reason=self.last_failure_reason or "excessive failures",
                retry_after=retry_after,
            )

    def record_success(self, now: float | None = None) -> None:
        """Records a successful operation."""
        n = now if now is not None else self._time_fn()
        self._prune_history(n)
        self._history.append((n, True))

        if self.state is CircuitState.HOLD:
            return

        self.consecutive_failures = 0
        if self.state is CircuitState.HALF_OPEN:
            self.consecutive_successes += 1
            if self.consecutive_successes >= self.consecutive_success_threshold:
                self.state = CircuitState.CLOSED
                self.opened_at = None

    def record_failure(
        self,
        reason: str = "operation failed",
        now: float | None = None,
    ) -> None:
        """Records an operational failure and updates circuit state."""
        n = now if now is not None else self._time_fn()
        self._prune_history(n)
        self._history.append((n, False))

        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure_reason = reason

        # 1. HOLD condition: consecutive failures reach hold_threshold
        if self.consecutive_failures >= self.hold_threshold:
            self.state = CircuitState.HOLD
            return

        # 2. In HALF_OPEN, any failure returns immediately to OPEN
        if self.state is CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.opened_at = n
            return

        # 3. In CLOSED, check failure threshold or error rate threshold
        if self.state is CircuitState.CLOSED:
            if self.consecutive_failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = n
                return

            if len(self._history) >= self.min_samples_for_rate:
                err_rate = self.error_rate(n)
                if err_rate >= self.error_rate_threshold:
                    self.state = CircuitState.OPEN
                    self.opened_at = n
                    self.last_failure_reason = (
                        f"error rate {err_rate:.2%} exceeded threshold {self.error_rate_threshold:.2%}"
                    )

    def trip_hold(self, reason: str = "manual or policy override") -> None:
        """Forces the circuit breaker into the HOLD state."""
        self.state = CircuitState.HOLD
        self.last_failure_reason = reason

    def reset(self) -> None:
        """Resets the circuit breaker to CLOSED (operator or creator action)."""
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.opened_at = None
        self.last_failure_reason = ""
        self._history.clear()


# ---------------------------------------------------------------------------
# Unified Provider Gate Limiter
# ---------------------------------------------------------------------------

class ProviderGateLimiter:
    """Unified gate limiter orchestrating rate limits, circuit breakers, and budgets."""

    def __init__(
        self,
        budget_enforcer: DynamicBudgetEnforcer | None = None,
        *,
        default_rate_requests: int | None = 60,
        default_rate_tokens: int | None = 100_000,
        rate_window_seconds: float = 60.0,
        failure_threshold: int = 5,
        hold_threshold: int = 10,
        recovery_timeout_seconds: float = 30.0,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        self.budget_enforcer = budget_enforcer or DynamicBudgetEnforcer()
        self.default_rate_requests = default_rate_requests
        self.default_rate_tokens = default_rate_tokens
        self.rate_window_seconds = rate_window_seconds
        self.failure_threshold = failure_threshold
        self.hold_threshold = hold_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self._time_fn = time_fn

        self._breakers: dict[str, CircuitBreaker] = {}
        self._rate_limiters: dict[str, SlidingWindowRateLimiter] = {}

    def get_breaker(self, provider_id: str) -> CircuitBreaker:
        if provider_id not in self._breakers:
            self._breakers[provider_id] = CircuitBreaker(
                provider_id,
                failure_threshold=self.failure_threshold,
                hold_threshold=self.hold_threshold,
                recovery_timeout_seconds=self.recovery_timeout_seconds,
                time_fn=self._time_fn,
            )
        return self._breakers[provider_id]

    def get_rate_limiter(self, provider_id: str) -> SlidingWindowRateLimiter:
        if provider_id not in self._rate_limiters:
            self._rate_limiters[provider_id] = SlidingWindowRateLimiter(
                max_requests=self.default_rate_requests,
                max_tokens=self.default_rate_tokens,
                window_seconds=self.rate_window_seconds,
                time_fn=self._time_fn,
            )
        return self._rate_limiters[provider_id]

    def before_call(
        self,
        provider_id: str,
        *,
        mission_id: str | None = None,
        estimated_tokens: int = 0,
        estimated_cost: float = 0.0,
        now: float | None = None,
    ) -> None:
        """Pre-flight check before dispatching a call to a provider.

        Enforces:
        1. Circuit Breaker state (fails fast if OPEN or HOLD).
        2. Hard Budget ceilings (fails fast if session or mission limit exceeded).
        3. Sliding-window Rate Limits (fails fast if request or token rate exceeded).
        """
        n = now if now is not None else self._time_fn()

        # 1. Circuit breaker check
        breaker = self.get_breaker(provider_id)
        breaker.check_request(n)

        # 2. Budget check
        self.budget_enforcer.check_budget(
            tokens=estimated_tokens,
            cost=estimated_cost,
            mission_id=mission_id,
        )

        # 3. Rate limiter acquire
        limiter = self.get_rate_limiter(provider_id)
        limiter.acquire(
            provider_id,
            requests=1,
            tokens=estimated_tokens,
            now=n,
        )

    def on_success(
        self,
        provider_id: str,
        *,
        mission_id: str | None = None,
        actual_tokens: int = 0,
        actual_cost: float = 0.0,
        now: float | None = None,
    ) -> None:
        """Post-call hook on successful provider execution."""
        n = now if now is not None else self._time_fn()
        breaker = self.get_breaker(provider_id)
        breaker.record_success(n)
        self.budget_enforcer.record_spend(
            tokens=actual_tokens,
            cost=actual_cost,
            mission_id=mission_id,
        )

    def on_failure(
        self,
        provider_id: str,
        *,
        reason: str = "provider call failed",
        now: float | None = None,
    ) -> None:
        """Post-call hook on provider failure."""
        n = now if now is not None else self._time_fn()
        breaker = self.get_breaker(provider_id)
        breaker.record_failure(reason=reason, now=n)


__all__ = [
    "BudgetExceeded",
    "CircuitBreaker",
    "CircuitBreakerError",
    "CircuitBreakerTripped",
    "CircuitState",
    "DynamicBudgetEnforcer",
    "HoldTripped",
    "ProviderGateLimiter",
    "RateLimitExceeded",
    "SlidingWindowRateLimiter",
]
