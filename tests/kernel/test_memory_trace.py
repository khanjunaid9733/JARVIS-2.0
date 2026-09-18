from __future__ import annotations

"""M2.1 episodic trace writer tests (spec §84.3 / §84.4 / §M2)."""

from jarvis.kernel.event_log import EventLog
from jarvis.kernel.memory_trace import (
    MEMORY_TRACE_RECORDED,
    MemoryTraceWriter,
)
from jarvis.kernel.registry import CREATOR_PRINCIPAL_ID


class _FixedClock:
    def __init__(self, ts: str = "2026-09-18T00:00:00.000Z") -> None:
        self._ts = ts

    def now_utc_iso(self) -> str:
        return self._ts


def _log(tmp_path, name: str = "log.db") -> EventLog:
    return EventLog(db_path=str(tmp_path / name), clock=_FixedClock())


def test_recorded_trace_emits_single_event_all_fields(tmp_path):
    log = _log(tmp_path)
    writer = MemoryTraceWriter(log)

    result = writer.record_episodic(
        content="read evidence.json which listed mission values",
        source="agent.run",
        evidence=["01ARZ3NDEKTSV4RRFFQ69G5FAV"],
        confidence=0.9,
    )

    assert result.status == "recorded"
    assert result.reason is None
    assert result.event_id is not None
    assert result.gate.passed is True

    events = log.replay()
    assert [event.event_type for event in events] == [MEMORY_TRACE_RECORDED]
    trace = events[0]
    assert trace.event_id == result.event_id
    assert trace.stream_id == "memory"
    assert trace.principal_id == CREATOR_PRINCIPAL_ID
    assert trace.cause_event_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert trace.correlation_id == result.event_id
    assert trace.payload["kind"] == "episodic"
    assert trace.payload["content"] == "read evidence.json which listed mission values"
    assert trace.payload["source"] == "agent.run"
    assert trace.payload["confidence"] == 0.9
    assert trace.payload["evidence"] == ["01ARZ3NDEKTSV4RRFFQ69G5FAV"]
    assert log.verify_chain() is True


def test_trace_without_evidence_has_no_cause_and_own_correlation(tmp_path):
    log = _log(tmp_path)
    result = MemoryTraceWriter(log).record_episodic(
        content="starting the umbrella project", source="agent"
    )

    trace = log.replay()[0]
    assert trace.cause_event_id is None
    assert trace.correlation_id == result.event_id


def test_evidence_links_last_element_as_cause(tmp_path):
    log = _log(tmp_path)
    MemoryTraceWriter(log).record_episodic(
        content="x", source="s", evidence=["first.ev", "last.ev"]
    )
    trace = log.replay()[0]
    assert trace.cause_event_id == "last.ev"
    assert trace.payload["evidence"] == ["first.ev", "last.ev"]


def test_confidence_is_clamped_not_rejected(tmp_path):
    log = _log(tmp_path)
    result = MemoryTraceWriter(log).record_episodic(
        content="overshot confidence", source="s", confidence=7.0
    )
    assert result.status == "recorded"
    assert log.replay()[0].payload["confidence"] == 1.0


def test_gate_failure_writes_no_event(tmp_path):
    log = _log(tmp_path)
    result = MemoryTraceWriter(log).record_episodic(content="", source="s")
    assert result.status == "rejected"
    assert result.event_id is None
    assert "content_present" in result.reason  # type: ignore[union-attr]
    assert log.replay() == []


def test_caller_principal_is_carried(tmp_path):
    log = _log(tmp_path)
    MemoryTraceWriter(log).record_episodic(
        content="self-recorded trace", source="agent-1", principal_id="model.agent"
    )
    assert log.replay()[0].principal_id == "model.agent"


def test_repeated_traces_append_in_order(tmp_path):
    log = _log(tmp_path)
    writer = MemoryTraceWriter(log)
    writer.record_episodic(content="first", source="s")
    writer.record_episodic(content="second", source="s")
    events = log.replay()
    assert [event.payload["content"] for event in events] == ["first", "second"]
    assert [event.stream_seq for event in events] == [1, 2]


# ---------------------------------------------------------------------------
# Antigravity M2.1 audit reconciliation (F-M2.1-1 / F-M2.1-2)
# ---------------------------------------------------------------------------

def test_trace_stamps_mission_id(tmp_path):
    """F-M2.1-1: traces recorded during a mission carry the mission_id."""
    log = _log(tmp_path)
    MemoryTraceWriter(log).record_episodic(
        content="evidence read during mission", source="agent.run", mission_id="M-42"
    )
    trace = log.replay()[0]
    assert trace.mission_id == "M-42"


def test_non_numeric_confidence_is_rejected_typed(tmp_path):
    """F-M2.1-2: non-numeric confidence returns a typed rejection, no raise."""
    log = _log(tmp_path)
    result = MemoryTraceWriter(log).record_episodic(
        content="bad confidence", source="s", confidence="high"
    )
    assert result.status == "rejected"
    assert result.event_id is None
    assert "confidence_valid" in result.reason  # type: ignore[union-attr]
    assert log.replay() == []