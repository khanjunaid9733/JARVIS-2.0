from __future__ import annotations

"""Module 10 memory write path tests (spec §84.4 / §127.1 / §112)."""

from jarvis.kernel.event_log import EventLog
from jarvis.kernel.memory_projection import MemoryProjection
from jarvis.kernel.memory_write import (
    MEMORY_COMMITTED,
    MEMORY_PROPOSED,
    MEMORY_REJECTED,
    MEMORY_VERIFIED,
    MemoryWriter,
)


class _FixedClock:
    def __init__(self, ts: str = "2026-09-18T00:00:00.000Z") -> None:
        self._ts = ts

    def now_utc_iso(self) -> str:
        return self._ts


def _log(tmp_path, name: str = "log.db") -> EventLog:
    return EventLog(db_path=str(tmp_path / name), clock=_FixedClock())


def test_committed_write_emits_three_events_and_projects(tmp_path):
    log = _log(tmp_path)
    writer = MemoryWriter(log)

    result = writer.remember(content="the safe word is umbrella", source="creator")

    assert result.status == "committed"
    assert result.reason is None
    assert [event.event_type for event in log.replay()] == [
        MEMORY_PROPOSED,
        MEMORY_VERIFIED,
        MEMORY_COMMITTED,
    ]
    assert log.verify_chain() is True

    projection = MemoryProjection.rebuild(log)
    assert list(projection.memories) == [result.event_ids[-1]]
    assert projection.memories[result.event_ids[-1]]["content"] == (
        "the safe word is umbrella"
    )


def test_proposed_and_verified_bracket_the_gate(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="x", source="s", confidence=0.4)

    _, verified, committed = log.replay()
    assert verified.payload["gate"]["passed"] is True
    assert committed.payload["confidence"] == 0.4
    assert "gate" not in committed.payload


def test_empty_content_is_rejected_and_not_promoted(tmp_path):
    log = _log(tmp_path)
    writer = MemoryWriter(log)

    result = writer.remember(content="", source="creator")

    assert result.status == "rejected"
    assert result.reason is not None
    types = [event.event_type for event in log.replay()]
    assert MEMORY_COMMITTED not in types
    assert types == [MEMORY_PROPOSED, MEMORY_VERIFIED, MEMORY_REJECTED]
    assert MemoryProjection.rebuild(log).memories == {}


def test_confidence_out_of_range_is_rejected(tmp_path):
    log = _log(tmp_path)
    result = MemoryWriter(log).remember(
        content="x", source="s", confidence=2.0
    )
    assert result.status == "rejected"
    assert MEMORY_COMMITTED not in [e.event_type for e in log.replay()]


def test_section_112_memory_promotion_requires_verification(tmp_path):
    """Rejected evidence must never yield a projected (promoted) memory."""
    log = _log(tmp_path)
    writer = MemoryWriter(log)

    writer.remember(content="valid", source="s")
    writer.remember(content="invalid", source="")  # missing source -> reject

    projection = MemoryProjection.rebuild(log)
    contents = [memory["content"] for memory in projection.memories.values()]
    assert contents == ["valid"]


def test_two_runs_with_same_clock_are_byte_deterministic(tmp_path):
    a = _log(tmp_path, name="a.db")
    b = _log(tmp_path, name="b.db")
    for log in (a, b):
        MemoryWriter(log).remember(content="c", source="s", confidence=0.5)

    def payloads(log: EventLog) -> list[dict]:
        return [event.payload for event in log.replay()]

    assert payloads(a) == payloads(b)
    assert [e.event_id for e in a.replay()] != [e.event_id for e in b.replay()]


def test_appended_memory_can_be_replayed_after_reopen(tmp_path):
    path = str(tmp_path / "log.db")
    log = _log(tmp_path)
    writer = MemoryWriter(log)
    result = writer.remember(content="persist me", source="creator")
    log.close()

    reopened = EventLog(db_path=path, clock=_FixedClock())
    projection = MemoryProjection.rebuild(reopened)
    assert result.event_ids[-1] in projection.memories
    assert projection.memories[result.event_ids[-1]]["content"] == "persist me"
    reopened.close()


# ---------------------------------------------------------------------------
# F-C9: non-creator authorship is a disclosed M1 default (provenance carried)
# ---------------------------------------------------------------------------

def test_non_creator_writer_commits_with_provenance(tmp_path):
    log = _log(tmp_path)
    writer = MemoryWriter(log, principal_id="model.agent")

    result = writer.remember(content="self-authored fact", source="agent-1")

    assert result.status == "committed"
    events = [e for e in log.replay() if e.event_type == MEMORY_COMMITTED]
    assert len(events) == 1
    assert events[0].principal_id == "model.agent"
    projection = MemoryProjection.rebuild(log)
    assert any(
        p.get("content") == "self-authored fact"
        for p in projection.memories.values()
    )
