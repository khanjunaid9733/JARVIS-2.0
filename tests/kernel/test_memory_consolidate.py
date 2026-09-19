from __future__ import annotations

"""M2.3 consolidation pipeline tests (spec §84.3 / docs/M2_3_KICKOFF.md,
ratified items A-E). Hermetic: no model calls, no effects, deterministic."""

import pytest

from jarvis.kernel.done_gate import DoneGate, GateCheck, GateDecision
from jarvis.kernel.event_log import EventLog
from jarvis.kernel.memory_api import Memory
from jarvis.kernel.memory_consolidate import (
    MEMORY_CONSOLIDATE_SUPERSEDED,
    ConsolidationPolicy,
    MemoryConsolidator,
)
from jarvis.kernel.memory_index import MemoryIndex
from jarvis.kernel.memory_trace import MemoryTraceWriter
from jarvis.kernel.memory_write import MemoryWriter

pytestmark = pytest.mark.anyio


class _FixedClock:
    def now_utc_iso(self) -> str:
        return "2026-09-18T00:00:00.000Z"


def _log(tmp_path, name: str = "consolidate.db") -> EventLog:
    return EventLog(db_path=str(tmp_path / name), clock=_FixedClock())


def _trace(log: EventLog, content: str, source: str, confidence: float = 0.8):
    result = MemoryTraceWriter(log=log).record_episodic(
        content=content, source=source, confidence=confidence
    )
    assert result.status == "recorded"
    return result.event_id


def _committed(log: EventLog, content: str, source: str, confidence: float = 1.0):
    result = MemoryWriter(log=log).remember(
        content=content, source=source, confidence=confidence
    )
    assert result.status == "committed"
    return result.event_ids[-1]


def _event_types(log: EventLog) -> list[str]:
    return [event.event_type for event in log.replay()]


def test_not_every_interaction_becomes_durable(tmp_path):
    log = _log(tmp_path)
    lonely = _trace(log, "The matching rule requires a badge reader", "agent")
    before = _event_types(log)

    result = MemoryConsolidator(log).consolidate()

    assert result.promoted == []
    assert result.skipped == {lonely: "below_evidence_min"}
    assert _event_types(log) == before


def test_evidence_min_reached_promotes_through_frozen_writer(tmp_path):
    log = _log(tmp_path)
    t1 = _trace(log, "The server public IP is 10.0.0.42.", "network.log")
    t2 = _trace(log, "The server public IP is 10.0.0.42.", "network.log")

    result = MemoryConsolidator(log).consolidate()

    assert len(result.promoted) == 1
    index = MemoryIndex.rebuild(log)
    promoted_id = result.promoted[0]
    payload = index.memories[promoted_id]
    assert payload["memory_class"] == "semantic"
    assert payload["provenance"]["evidence_ids"] == [t1, t2]
    assert index.traces[t1]["content"] == payload["content"]
    assert _event_types(log) == [
        "memory.trace.recorded",
        "memory.trace.recorded",
        "memory.write.proposed",
        "memory.write.verified",
        "memory.write.committed",
    ]


def test_idempotent_rerun_emits_nothing(tmp_path):
    log = _log(tmp_path)
    _trace(log, "The safe word prefix is umbrella", "captain")
    _trace(log, "The safe word prefix is umbrella", "captain")

    first = MemoryConsolidator(log).consolidate()
    before = _event_types(log)

    second = MemoryConsolidator(log).consolidate()

    assert len(first.promoted) == 1
    assert second.promoted == []
    assert second.skipped == {}
    assert _event_types(log) == before


def test_contradiction_supersedes_old_memory(tmp_path):
    log = _log(tmp_path)
    old_id = _committed(log, "The server command channel is rpc-1.", "ops", 0.5)
    t1 = _trace(log, "The  server command channel is rpc-1.", "ops", confidence=0.95)
    t2 = _trace(log, "The server command channel is rpc-1.", "ops", confidence=0.95)

    result = MemoryConsolidator(log).consolidate()

    assert list(result.superseded) == [old_id]
    index = MemoryIndex.rebuild(log)
    new_id = result.promoted[0]
    assert result.superseded[old_id] == new_id
    assert index.memories[new_id]["content"] == "The server command channel is rpc-1."
    assert index.memories[new_id]["provenance"]["superseded"] == [old_id]
    assert index.memories[old_id]  # append-only: old memory still folded
    supersede = [
        e
        for e in log.replay()
        if e.event_type == MEMORY_CONSOLIDATE_SUPERSEDED
    ]
    assert len(supersede) == 1
    assert supersede[0].payload["old_event_id"] == old_id
    assert supersede[0].payload["new_event_id"] == new_id


def test_supersede_events_never_enter_memoryindex_folds(tmp_path):
    log = _log(tmp_path)
    _committed(log, "The server command channel is rpc-1.", "ops", confidence=0.5)
    _trace(log, "The server command channel is rpc-1.", "ops", confidence=0.95)
    _trace(log, "The  server command channel is rpc-1.", "ops", confidence=0.95)

    MemoryConsolidator(log).consolidate()

    index = MemoryIndex.rebuild(log)
    assert len(index.memories) == 2  # old + new; no entries for audit events
    assert index.event_count == len(_event_types(log))
    assert len(
        [e for e in log.replay() if e.event_type == MEMORY_CONSOLIDATE_SUPERSEDED]
    ) == 1


def test_policy_is_decision_table_not_branches(tmp_path):
    strict = ConsolidationPolicy(extract={"evidence_min": 3})
    loose = ConsolidationPolicy(extract={"evidence_min": 2})

    log_a = _log(tmp_path, "a.db")
    for _ in range(2):
        _trace(log_a, "The build variant is release.", "ci")
    result_a = MemoryConsolidator(log_a, policy=strict).consolidate()
    assert result_a.promoted == []

    log_b = _log(tmp_path, "b.db")
    for _ in range(2):
        _trace(log_b, "The build variant is release.", "ci")
    result_b = MemoryConsolidator(log_b, policy=loose).consolidate()
    assert len(result_b.promoted) == 1


def test_gate_failure_skips_not_raises(tmp_path):
    log = _log(tmp_path)
    t1 = _trace(log, "The quick brown fox jumps over the lazy dog again.", "probe")
    t2 = _trace(log, "The quick brown fox jumps over the lazy dog again.", "probe")

    class _FailingGate:
        def evaluate(self, kind, evidence):
            return GateDecision(
                kind=kind,
                passed=False,
                checks=[
                    GateCheck(name="confidence_valid", passed=False, detail="no")
                ],
            )

    result = MemoryConsolidator(log, gate=_FailingGate()).consolidate()

    assert result.promoted == []
    assert result.skipped == {
        t1: "verification_failed",
        t2: "verification_failed",
    }
    assert all(
        not e.event_type.startswith("memory.write")
        for e in log.replay()
    )


def test_confidence_floor_gates_promotion(tmp_path):
    log = _log(tmp_path)
    t1 = _trace(log, "The threshold setting is zero point five.", "tuner", confidence=0.5)
    t2 = _trace(log, "The threshold setting is zero point five.", "tuner", confidence=0.5)

    policy = ConsolidationPolicy(promote={"confidence_floor": 0.9})
    result = MemoryConsolidator(log, policy=policy).consolidate()

    assert result.promoted == []
    assert result.skipped == {
        t1: "confidence_below_floor",
        t2: "confidence_below_floor",
    }


def test_facade_consolidates_with_own_log(tmp_path):
    log = _log(tmp_path)
    _trace(log, "The deployment target is east-1.", "deploy")
    _trace(log, "The deployment target is east-1.", "deploy")

    result = Memory(log=log).consolidate()

    assert len(result.promoted) == 1
    assert Memory(log=log).memory_count == 1


def test_facade_consolidate_requires_event_log(tmp_path):
    log = _log(tmp_path)
    index = MemoryIndex.rebuild(log)

    with pytest.raises(ValueError, match="requires an EventLog"):
        Memory(index=index).consolidate()


def test_single_followup_trace_does_not_repromote(tmp_path):
    log = _log(tmp_path)
    _trace(log, "The server public IP is 10.0.0.42.", "network.log")
    _trace(log, "The server public IP is 10.0.0.42.", "network.log")
    MemoryConsolidator(log).consolidate()
    _trace(log, "The server public IP is 10.0.0.42.", "network.log")

    result = MemoryConsolidator(log).consolidate()

    assert result.promoted == []
    assert list(result.skipped.values()) == ["below_evidence_min"]


def test_contradiction_no_win_keeps_existing_memory(tmp_path):
    log = _log(tmp_path)
    _committed(log, "The server command channel is rpc-1.", "ops", confidence=0.99)
    t1 = _trace(log, "The server command channel is rpc-1.", "ops", confidence=0.5)
    t2 = _trace(log, "The server command channel is rpc-1.", "ops", confidence=0.5)

    policy = ConsolidationPolicy(
        contradiction={"supersede_evidence_min": 3}
    )
    result = MemoryConsolidator(log, policy=policy).consolidate()

    assert result.promoted == []
    assert result.skipped == {
        t1: "collides_with_committed",
        t2: "collides_with_committed",
    }