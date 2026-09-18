from __future__ import annotations

"""Module 10 deterministic done-gate tests (spec §81.3 / §112 / NAT-05)."""

import pytest

from jarvis.kernel.done_gate import (
    CHECKS,
    COMPLETION_EVENT_TYPE,
    COMPLETION_REFUSED_EVENT_TYPE,
    GATE_REQUIREMENTS,
    CompletionGate,
    DoneGate,
)
from jarvis.kernel.event_log import EventLog


class _FixedClock:
    def __init__(self, ts: str) -> None:
        self._ts = ts

    def now_utc_iso(self) -> str:
        return self._ts


def _log(tmp_path, name: str = "log.db") -> EventLog:
    return EventLog(
        db_path=str(tmp_path / name),
        clock=_FixedClock("2026-09-18T00:00:00.000Z"),
    )


# ---------------------------------------------------------------------------
# Pure gate evaluation
# ---------------------------------------------------------------------------

def test_requirements_are_registered_data():
    assert GATE_REQUIREMENTS["memory.write"] == (
        "content_present",
        "source_present",
        "confidence_valid",
    )
    assert set(GATE_REQUIREMENTS["memory.write"]) <= set(CHECKS)


def test_unknown_kind_raises_keyerror():
    with pytest.raises(KeyError):
        DoneGate().evaluate("no.such.kind", {})


def test_valid_memory_evidence_passes_all_checks():
    decision = DoneGate().evaluate(
        "memory.write",
        {"content": "the safe word is umbrella", "source": "creator", "confidence": 1.0},
    )
    assert decision.passed is True
    assert decision.check("content_present") is True
    assert decision.check("source_present") is True
    assert decision.check("confidence_valid") is True


def test_empty_content_fails_with_detail():
    decision = DoneGate().evaluate(
        "memory.write", {"content": "  ", "source": "creator", "confidence": 1.0}
    )
    assert decision.passed is False
    assert decision.check("content_present") is False


def test_missing_source_fails():
    decision = DoneGate().evaluate(
        "memory.write", {"content": "x", "confidence": 1.0}
    )
    assert decision.passed is False
    assert decision.check("source_present") is False


@pytest.mark.parametrize("bad", [-0.1, 1.1, "high", None, True])
def test_invalid_confidence_fails(bad):
    decision = DoneGate().evaluate(
        "memory.write", {"content": "x", "source": "s", "confidence": bad}
    )
    assert decision.passed is False
    assert decision.check("confidence_valid") is False


def test_decision_check_lookup_on_unknown_check_raises():
    decision = DoneGate().evaluate(
        "memory.write", {"content": "x", "source": "s", "confidence": 0.5}
    )
    with pytest.raises(KeyError):
        decision.check("nope")


def test_evaluation_is_pure_and_repeatable():
    gate = DoneGate()
    evidence = {"content": "x", "source": "s", "confidence": 0.5}
    assert gate.evaluate("memory.write", evidence) == gate.evaluate(
        "memory.write", evidence
    )


# ---------------------------------------------------------------------------
# NAT-05: agent cannot self-declare completion
# ---------------------------------------------------------------------------

def test_nat_05_completion_without_evidence_is_refused(tmp_path):
    log = _log(tmp_path)
    gate = CompletionGate(log, principal_id="model.agent")

    decision = gate.declare_completion(task_id="t1", evidence={})

    assert decision.passed is False
    types = [event.event_type for event in log.replay()]
    assert types == [COMPLETION_REFUSED_EVENT_TYPE]
    assert COMPLETION_EVENT_TYPE not in types


def test_nat_05_partial_evidence_still_refused(tmp_path):
    log = _log(tmp_path)
    gate = CompletionGate(log, principal_id="model.agent")

    decision = gate.declare_completion(
        task_id="t1", evidence={"artifact": "plan.md"}
    )

    assert decision.passed is False
    assert [event.event_type for event in log.replay()] == [
        COMPLETION_REFUSED_EVENT_TYPE
    ]


def test_completion_with_objective_evidence_is_emitted(tmp_path):
    log = _log(tmp_path)
    gate = CompletionGate(log, principal_id="model.agent")

    decision = gate.declare_completion(
        task_id="t1",
        mission_id="m1",
        evidence={"artifact": "plan.md", "verification": "tests passed: 3/3"},
    )

    assert decision.passed is True
    events = log.replay()
    assert [event.event_type for event in events] == [COMPLETION_EVENT_TYPE]
    assert events[0].task_id == "t1"
    assert events[0].mission_id == "m1"
    assert log.verify_chain() is True
