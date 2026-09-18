from __future__ import annotations

"""M2.1 Memory API facade tests (spec §M2)."""

import pytest

from jarvis.kernel.event_log import Event, EventLog
from jarvis.kernel.memory_api import Memory
from jarvis.kernel.memory_index import MemoryIndex
from jarvis.kernel.memory_projection import MemoryProjection
from jarvis.kernel.memory_query import recall as module11_recall
from jarvis.kernel.memory_trace import MemoryTraceWriter
from jarvis.kernel.memory_write import MemoryWriter


class _FixedClock:
    def now_utc_iso(self) -> str:
        return "2026-09-18T00:00:00.000Z"


def _log(tmp_path) -> EventLog:
    return EventLog(db_path=str(tmp_path / "log.db"), clock=_FixedClock())


def test_recall_unions_memories_and_traces(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="the capital of France is Paris", source="s")
    MemoryTraceWriter(log).record_episodic(
        content="the safe word is umbrella", source="agent.run"
    )

    hits = Memory(log=log).recall("what is the safe word?", limit=3)

    assert len(hits) == 1
    assert hits[0].content == "the safe word is umbrella"
    assert hits[0].score == 1.0


def test_recall_signals_memory_and_trace_scores_total_order(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="umbrella is a company", source="s")
    MemoryTraceWriter(log).record_episodic(
        content="safe word umbrella", source="agent.run"
    )

    hits = Memory(log=log).recall("umbrella", limit=3)

    assert len(hits) == 2
    scores = [hit.score for hit in hits]
    assert scores == sorted(scores, reverse=True)
    assert hits[0].content != hits[1].content
    # tie-break is (-score, event_id): equal scores must be stably ordered
    if scores[0] == scores[1]:
        assert hits[0].event_id < hits[1].event_id


def test_recall_with_no_traces_matches_module_11_bit_identical(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="the capital of France is Paris", source="s")

    projection = MemoryProjection.rebuild(log)
    expected = module11_recall(projection, "what is the capital of France?", limit=3)
    actual = Memory(projection=projection).recall(
        "what is the capital of France?", limit=3
    )

    assert actual == expected


def test_get_returns_memory_and_trace_payloads(tmp_path):
    log = _log(tmp_path)
    mem = MemoryWriter(log).remember(content="alpha", source="s")
    trace = MemoryTraceWriter(log).record_episodic(content="beta", source="s")

    memory = Memory(log=log)
    assert memory.get(mem.event_ids[-1])["content"] == "alpha"
    assert memory.get(trace.event_id)["content"] == "beta"  # type: ignore[union-attr]
    assert memory.get("01NOSUCHULID0000000000000") is None


def test_counts_and_digest(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="alpha", source="s")
    MemoryTraceWriter(log).record_episodic(content="beta", source="s")

    memory = Memory(log=log)
    assert memory.memory_count == 1
    assert memory.trace_count == 1
    assert len(memory.digest()) == 64
    assert memory.digest() == Memory(log=log).digest()


def test_projection_fallback_recall_equals_module_11_lexical(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="umbrella is the safe word", source="s")
    projection = MemoryProjection.rebuild(log)

    actual = Memory(projection=projection).recall("safe word", limit=1)
    expected = module11_recall(projection, "safe word", limit=1)
    assert actual == expected


def test_constructor_requires_an_input(tmp_path):
    with pytest.raises(ValueError):
        Memory()


# ---------------------------------------------------------------------------
# Antigravity M2.1 audit reconciliation (F-M2.1-3 / F-M2.1-4)
# ---------------------------------------------------------------------------

def test_get_returns_empty_memory_payload_not_none(tmp_path):
    """F-M2.1-3: an empty committed payload must still resolve via get()."""
    log = _log(tmp_path)
    event_id = log.append(
        Event(
            stream_id="memory",
            event_type="memory.write.committed",
            principal_id="creator",
            payload={},
        )
    )
    assert Memory(log=log).get(event_id) == {}


def test_backend_slots_always_materialized(tmp_path):
    """F-M2.1-4: both _index and _projection slots exist on every Memory."""
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="alpha", source="s")

    by_index = Memory(index=MemoryIndex.rebuild(log))
    assert by_index.index is not None
    assert by_index.recall("alpha")

    by_log = Memory(log=log)
    assert by_log.index is not None
    assert by_log.recall("alpha")

    by_projection = Memory(projection=MemoryProjection.rebuild(log))
    assert by_projection.index is None
    assert by_projection.recall("alpha")