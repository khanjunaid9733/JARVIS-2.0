from __future__ import annotations

"""Deterministic budget accounting ledger (module 16, STRETCH M1.1, §80.4).

§80.4 budgets resources per mission/agent (`budget: {tokens, wall_seconds}`);
§134.1 STRETCH asks for "budget accounting display". M1.1 has no agent
runtime, so this module folds the accounting REALITY that exists: every
`question.asked` audit event (module 15) on the gateway path, plus any
`mission.started` allocation declared on a mission stream (module 14 intake).

The fold is pure and ordered (replay order), mirroring the
`MemoryProjection` / `MissionLifecycle` precedents. It writes nothing and
has no clock/RNG; identical logs produce identical ledgers (G20/NAT-03).

Honest accounting only: `spent_tokens` reflects what `question.asked`
events actually carried. The module-6 adapter does not surface `usage`, so
today that sum is 0 and is displayed as "0 tokens accounted" — the seam
(`tokens` payload key) is forward-compatible with an adapter that reports
it. A declared allocation (`mission.started` payload `budget.tokens`) sets
`allocation_tokens`; without one, allocation is `None` (unbounded).
"""

from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict

from .event_log import Event
from .mission_lifecycle import MISSION_STARTED
from .model_answer import QUESTION_ASKED, SESSION_STREAM_ID

_DEFAULT_STREAM = SESSION_STREAM_ID


class StreamBudget(BaseModel):
    """Accounting slab for one stream (a session or a mission)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    stream_id: str
    model_calls: int = 0
    deterministic_fallbacks: int = 0
    attempts: int = 0
    spent_tokens: int = 0
    allocation_tokens: int | None = None
    first_asked_event_id: str | None = None

    @property
    def questions(self) -> int:
        return self.model_calls + self.deterministic_fallbacks

    @property
    def allocation(self) -> str:
        return (
            str(self.allocation_tokens)
            if self.allocation_tokens is not None
            else "unbounded"
        )


class BudgetLedger(BaseModel):
    """Frozen fold result: per-stream budgets keyed by stream_id."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    streams: dict[str, StreamBudget] = {}

    @classmethod
    def rebuild(
        cls,
        events: Iterable[Event],
        *,
        default_stream_id: str = _DEFAULT_STREAM,
    ) -> "BudgetLedger":
        raw: dict[str, dict[str, Any]] = {}

        def _slab(stream_id: str) -> dict[str, Any]:
            return raw.setdefault(
                stream_id,
                {
                    "stream_id": stream_id,
                    "model_calls": 0,
                    "deterministic_fallbacks": 0,
                    "attempts": 0,
                    "spent_tokens": 0,
                    "allocation_tokens": None,
                    "first_asked_event_id": None,
                },
            )

        for event in events:
            # Accounting key: a mission-scoped event folds under its
            # mission_id (per-mission budget, §80.4); otherwise its stream.
            key = event.mission_id or event.stream_id or default_stream_id
            if event.event_type == QUESTION_ASKED:
                slab = _slab(key)
                if event.payload.get("fallback") == "model":
                    slab["model_calls"] += 1
                else:
                    slab["deterministic_fallbacks"] += 1
                slab["attempts"] += int(event.payload.get("attempts") or 0)
                tokens = event.payload.get("tokens")
                if isinstance(tokens, int) and tokens >= 0:
                    slab["spent_tokens"] += tokens
                if slab["first_asked_event_id"] is None:
                    slab["first_asked_event_id"] = event.event_id
            elif event.event_type == MISSION_STARTED and event.mission_id:
                allocation = _declared_allocation(event.payload)
                if allocation is not None:
                    _slab(event.mission_id)["allocation_tokens"] = allocation

        streams = {
            key: StreamBudget.model_validate(slab) for key, slab in sorted(raw.items())
        }
        return cls(streams=streams)

    def stream_budget(self, stream_id: str) -> StreamBudget | None:
        return self.streams.get(stream_id)

    def total(self) -> StreamBudget:
        if not self.streams:
            return StreamBudget(stream_id="*")
        return StreamBudget(
            stream_id="*",
            model_calls=sum(s.model_calls for s in self.streams.values()),
            deterministic_fallbacks=sum(
                s.deterministic_fallbacks for s in self.streams.values()
            ),
            attempts=sum(s.attempts for s in self.streams.values()),
            spent_tokens=sum(s.spent_tokens for s in self.streams.values()),
            allocation_tokens=None,
            first_asked_event_id=None,
        )


def _declared_allocation(payload: dict[str, Any] | None) -> int | None:
    """`mission.started` payload allocation: `{"budget": {"tokens": N}}` or the
    flattened `{"budget_tokens": N}`. Non-int values are ignored (refuses to
    fabricate an allocation)."""
    if not payload:
        return None
    budget = payload.get("budget")
    if isinstance(budget, dict):
        tokens = budget.get("tokens")
        if isinstance(tokens, int) and tokens >= 0:
            return tokens
    flat = payload.get("budget_tokens")
    if isinstance(flat, int) and flat >= 0:
        return flat
    return None