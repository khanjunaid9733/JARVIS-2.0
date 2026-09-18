from __future__ import annotations

"""Module 16 budget accounting ledger tests (STRETCH M1.1, §80.4).

The ledger folds `Event` objects (no DB needed): `question.asked` + 
`mission.started` allocations, all pure and replay-order deterministic.
"""

from jarvis.kernel.budget_ledger import BudgetLedger, StreamBudget
from jarvis.kernel.event_log import Event
from jarvis.kernel.mission_lifecycle import MISSION_STARTED, MISSION_STREAM_ID
from jarvis.kernel.model_answer import QUESTION_ASKED, SESSION_STREAM_ID


def _asked(
    *,
    fallback: str = "model",
    attempts: int = 1,
    tokens: int | None = None,
    mission_id: str | None = None,
    stream_id: str = SESSION_STREAM_ID,
    event_id: str = "",
) -> Event:
    return Event(
        event_id=event_id or f"ask-{fallback}-{attempts}-{tokens}",
        stream_id=stream_id,
        event_type=QUESTION_ASKED,
        principal_id="creator",
        mission_id=mission_id,
        payload={
            "question": "q",
            "fallback": fallback,
            "provider_id": "model.adapter",
            "attempts": attempts,
            "tokens": tokens,
            "failure_reason": None,
        },
    )


def _mission_started(mission_id: str, budget_tokens: int | None = None) -> Event:
    budget = {"budget": {"tokens": budget_tokens}} if budget_tokens is not None else {}
    return Event(
        event_id=f"start-{mission_id}",
        stream_id=MISSION_STREAM_ID,
        event_type=MISSION_STARTED,
        principal_id="creator",
        mission_id=mission_id,
        payload=budget,
    )


def test_empty_ledger_has_no_streams():
    ledger = BudgetLedger.rebuild([])
    assert ledger.streams == {}
    assert ledger.stream_budget(SESSION_STREAM_ID) is None
    total = ledger.total()
    assert total.model_calls == 0
    assert total.deterministic_fallbacks == 0
    assert total.spent_tokens == 0


def test_model_and_fallback_call_accounting_sums_attempts_and_tokens():
    ledger = BudgetLedger.rebuild(
        [
            _asked(fallback="model", attempts=1, tokens=None),
            _asked(fallback="model", attempts=2, tokens=40),
            _asked(fallback="deterministic", attempts=3, tokens=12),
        ]
    )
    slab = ledger.stream_budget(SESSION_STREAM_ID)
    assert slab is not None
    assert slab.model_calls == 2
    assert slab.deterministic_fallbacks == 1
    assert slab.questions == 3
    assert slab.attempts == 6
    assert slab.spent_tokens == 52
    assert slab.allocation_tokens is None
    assert slab.allocation == "unbounded"
    assert ledger.total().model_calls == 2


def test_non_int_or_negative_tokens_are_not_accounted():
    ledger = BudgetLedger.rebuild(
        [
            _asked(fallback="model", tokens=-5),
            Event(
                event_id="ask-neg",
                stream_id=SESSION_STREAM_ID,
                event_type=QUESTION_ASKED,
                principal_id="creator",
                payload={"question": "q", "fallback": "model", "tokens": "9000"},
            ),
        ]
    )
    slab = ledger.stream_budget(SESSION_STREAM_ID)
    assert slab is not None
    assert slab.model_calls == 2
    assert slab.spent_tokens == 0


def test_mission_allocation_folds_to_mission_stream():
    ledger = BudgetLedger.rebuild(
        [
            _mission_started("m-1", budget_tokens=20000),
            _asked(fallback="model", mission_id="m-1"),
            _asked(fallback="model"),
        ]
    )
    mission = ledger.stream_budget("m-1")
    assert mission is not None
    assert mission.allocation_tokens == 20000
    assert mission.allocation == "20000"
    assert mission.model_calls == 1
    session = ledger.stream_budget(SESSION_STREAM_ID)
    assert session is not None
    assert session.model_calls == 1
    assert session.allocation_tokens is None


def test_flat_allocation_and_ignored_invalid_allocations():
    ledger = BudgetLedger.rebuild(
        [
            _mission_started("m-flat"),
            Event(
                event_id="start-flat",
                stream_id=MISSION_STREAM_ID,
                event_type=MISSION_STARTED,
                principal_id="creator",
                mission_id="m-flat",
                payload={"budget_tokens": 500},
            ),
            _mission_started("m-bad"),
            Event(
                event_id="start-bad",
                stream_id=MISSION_STREAM_ID,
                event_type=MISSION_STARTED,
                principal_id="creator",
                mission_id="m-bad",
                payload={"budget": {"tokens": "not-an-int"}},
            ),
        ]
    )
    assert ledger.stream_budget("m-flat").allocation_tokens == 500
    assert (
        ledger.stream_budget("m-bad") is None
    ), "invalid allocation must not create a budget slab"


def test_streams_sorted_and_first_asked_event_recorded():
    ledger = BudgetLedger.rebuild([_asked(fallback="model", event_id="zzz")])
    assert list(ledger.streams) == sorted(ledger.streams)
    slab = ledger.stream_budget(SESSION_STREAM_ID)
    assert slab.first_asked_event_id == "zzz"