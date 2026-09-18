from __future__ import annotations

"""M2.1 MemoryIndex projection tests (spec §84.3 tier 1 / NAT-03)."""

from jarvis.kernel.event_log import EventLog
from jarvis.kernel.memory_index import MemoryIndex
from jarvis.kernel.memory_trace import MemoryTraceWriter
from jarvis.kernel.memory_write import MemoryWriter


class _FixedClock:
    def __init__(self, ts: str = "2026-09-18T00:00:00.000Z") -> None:
        self._ts = ts

    def now_utc_iso(self) -> str:
        return self._ts


def _log(tmp_path, name: str = "log.db") -> EventLog:
    return EventLog(db_path=str(tmp_path / name), clock=_FixedClock())


def test_index_folds_committed_memories_and_traces(tmp_path):
    log = _log(tmp_path)
    mem = MemoryWriter(log).remember(content="the capital of France is Paris", source="s")
    trace = MemoryTraceWriter(log).record_episodic(
        content="read evidence.json", source="agent.run"
    )

    index = MemoryIndex.rebuild(log)
    assert len(index.memories) == 1
    assert len(index.traces) == 1
    assert mem.event_ids[-1] in index.memories
    assert trace.event_id in index.traces
    assert index.memories[mem.event_ids[-1]]["content"] == (
        "the capital of France is Paris"
    )
    assert index.traces[trace.event_id]["content"] == "read evidence.json"


def test_index_excludes_proposed_verified_rejected(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="", source="")
    MemoryTraceWriter(log).record_episodic(content="", source="")
    index = MemoryIndex.rebuild(log)
    assert index.memories == {}
    assert index.traces == {}
    assert index.event_count == 3  # proposed/verified/rejected; empty trace writes nothing


def test_rebuild_is_deterministic_digest_stable(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="alpha", source="s")
    MemoryTraceWriter(log).record_episodic(content="beta", source="s")

    first = MemoryIndex.rebuild(log)
    second = MemoryIndex.rebuild(log)
    assert first == second
    assert first.digest() == second.digest()


def test_tamper_halts_rebuild_like_module_7(tmp_path):
    import json

    log = _log(tmp_path)
    MemoryWriter(log).remember(content="tamper target", source="s")
    with log._conn:
        log._conn.execute("DROP TRIGGER IF EXISTS events_no_update")
        log._conn.execute(
            "UPDATE events SET payload_json = ? WHERE event_type = 'memory.write.committed'",
            (json.dumps({"content": "tampered"}),),
        )
    try:
        MemoryIndex.rebuild(log)
        raise AssertionError("rebuild must halt on tampering (NAT-04)")
    except Exception as exc:
        assert "mismatch" in str(exc)