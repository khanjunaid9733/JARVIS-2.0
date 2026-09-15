import asyncio
import json
import sqlite3

import pytest

from jarvis.kernel.event_log import (
    Event,
    EventIntegrityError,
    EventLog,
    EventLogError,
    SystemClock,
    new_ulid,
)


class _FakeClock:
    def __init__(self) -> None:
        self.t = 1726300000.123

    def now_utc_iso(self) -> str:
        iso = str(self.t)
        self.t += 1.0
        return iso


def _make_log(tmp_path, clock=None) -> EventLog:
    return EventLog(db_path=str(tmp_path / "log.db"), clock=clock or _FakeClock())


def _event(**overrides) -> Event:
    base = dict(
        stream_id="memory",
        event_type="memory.write",
        principal_id="creator",
        payload={"content": "hello", "tags": ["a"]},
    )
    base.update(overrides)
    return Event(**base)


@pytest.fixture
def clock():
    return _FakeClock()


def test_append_returns_ulid(tmp_path, clock):
    log = _make_log(tmp_path, clock)
    eid = log.append(_event())
    assert len(eid) == 26
    assert all(c in "0123456789ABCDEFGHJKMNPQRSTVWXYZ" for c in eid)
    log.close()


def test_append_assigns_stream_seq_and_ts(tmp_path, clock):
    log = _make_log(tmp_path, clock)
    eid1 = log.append(_event(stream_id="s1"))
    eid2 = log.append(_event(stream_id="s1"))
    events = log.replay()
    assert [e.stream_seq for e in events] == [1, 2]
    assert events[0].ts_utc == "1726300000.123"
    assert events[0].event_id == eid1
    log.close()


def test_stream_is_async_iterator_and_ordered(tmp_path, clock):
    log = _make_log(tmp_path, clock)
    for i in range(5):
        log.append(_event(stream_id=f"st{i % 2}", payload={"i": i}))

    async def collect():
        out = []
        async for ev in log.stream():
            out.append(ev)
        return out

    events = asyncio.run(collect())
    assert [e.stream_seq for e in events] == [1, 1, 2, 2, 3]
    assert [e.payload["i"] for e in events] == [0, 1, 2, 3, 4]
    log.close()


def test_stream_filters(tmp_path, clock):
    log = _make_log(tmp_path, clock)
    log.append(_event(stream_id="s1", event_type="memory.write", mission_id="m1"))
    log.append(_event(stream_id="s2", event_type="memory.read", mission_id="m1"))
    log.append(_event(stream_id="s3", event_type="task.say", mission_id="m2"))

    async def by_type():
        out = []
        async for ev in log.stream(event_type="memory.write"):
            out.append(ev)
        return out

    async def by_stream():
        out = []
        async for ev in log.stream(stream_id="s2"):
            out.append(ev)
        return out

    async def by_stream_seq_since():
        out = []
        async for ev in log.stream(since=1, mission_id="m1"):
            out.append(ev)
        return out

    assert [e.event_type for e in asyncio.run(by_type())] == ["memory.write"]
    assert [e.stream_id for e in asyncio.run(by_stream())] == ["s2"]
    assert [e.stream_id for e in asyncio.run(by_stream_seq_since())] == ["s2"]
    log.close()


def test_wal_journal_mode_enabled(tmp_path, clock):
    log = _make_log(tmp_path, clock)
    mode = log._conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"
    log.close()


def test_append_only_triggers_deny_update_and_delete(tmp_path, clock):
    log = _make_log(tmp_path, clock)
    log.append(_event())
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        log._conn.execute("UPDATE events SET event_type='x'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        log._conn.execute("DELETE FROM events")
    log.close()


def test_append_assigns_stream_seq_authoritatively(tmp_path, clock):
    """append() owns stream_seq: caller-provided values are reassigned sequentially."""
    log = _make_log(tmp_path, clock)
    log.append(_event(stream_id="s1", stream_seq=99))
    log.append(_event(stream_id="s1", stream_seq=7))
    events = log.replay()
    assert [e.stream_seq for e in events] == [1, 2]
    log.close()


def test_unique_stream_seq_constraint_blocks_raw_duplicate(tmp_path, clock):
    """The (stream_id, stream_seq) UNIQUE constraint rejects duplicates at the DB layer."""
    log = _make_log(tmp_path, clock)
    log.append(_event(stream_id="s1"))
    with pytest.raises(sqlite3.IntegrityError):
        log._conn.execute(
            """
            INSERT INTO events (
                event_id, stream_id, stream_seq, ts_utc, event_type,
                schema_version, principal_id, payload_json, payload_sha256,
                prev_event_sha256, event_sha256
            ) VALUES ('T', 's1', 1, 'x', 't', 1, 'p', 'ph', '{"a":1}', NULL, 'eh')
            """
        )
    log.close()


def test_verify_chain_true_after_appends(tmp_path, clock):
    log = _make_log(tmp_path, clock)
    for i in range(20):
        log.append(_event(payload={"i": i}))
    assert log.verify_chain() is True
    log.close()


def test_nat_03_replay_identical_log_twice_byte_identical(tmp_path, clock):
    """NAT-03: replaying the identical event log twice yields byte-identical hashes.

    INTERIM proxy: this digests the raw event stream via projection_digest().
    When the minimal memory projection lands (spec §134.1), NAT-03 must be
    rewritten to digest that projection's output. Do NOT re-mark NAT-03 done
    without re-verifying against the projection.
    """
    log = _make_log(tmp_path, clock)
    for i in range(10):
        log.append(_event(stream_id="memory", payload={"i": i}))

    d1 = log.projection_digest()
    log.close()

    log2 = _make_log(tmp_path, clock)
    d2 = log2.projection_digest()

    assert d1 == d2
    assert log2.last_seq() == 10
    log2.close()


def test_nat_04_tampered_payload_halts_replay(tmp_path, clock):
    """NAT-04: a tampered event row (payload/hash mismatch) halts replay."""
    log = _make_log(tmp_path, clock)
    log.append(_event(payload={"content": "safe"}))
    log.append(_event(payload={"content": "target"}))
    log.append(_event(payload={"content": "bridge"}))
    assert log.verify_chain() is True

    tbl = sqlite3.connect(str(tmp_path / "log.db"))
    tbl.execute("DROP TRIGGER IF EXISTS events_no_update")
    tbl.execute(
        "UPDATE events SET payload_json = ? WHERE seq = 2",
        (json.dumps({"content": "tampered"}),),
    )
    tbl.commit()
    tbl.close()

    assert log.verify_chain() is False
    with pytest.raises(EventIntegrityError):
        log.replay()
    log.close()


def test_nat_04_tampered_payload_mid_chain_halts_replay(tmp_path, clock):
    """NAT-04: tampering a middle row breaks both downstream chaining checks."""
    log = _make_log(tmp_path, clock)
    for i in range(6):
        log.append(_event(payload={"i": i}))
    assert log.verify_chain() is True

    tbl = sqlite3.connect(str(tmp_path / "log.db"))
    tbl.execute("DROP TRIGGER IF EXISTS events_no_update")
    tbl.execute(
        "UPDATE events SET payload_json = ? WHERE seq = 4",
        (json.dumps({"i": 999}),),
    )
    tbl.commit()
    tbl.close()

    assert log.verify_chain() is False
    with pytest.raises(EventIntegrityError):
        log.replay()
    log.close()


def test_nat_04_tampered_prev_hash_halts_replay(tmp_path, clock):
    """NAT-04: tampering the chain pointer also halts replay."""
    log = _make_log(tmp_path, clock)
    for i in range(4):
        log.append(_event(payload={"i": i}))

    tbl = sqlite3.connect(str(tmp_path / "log.db"))
    tbl.execute("DROP TRIGGER IF EXISTS events_no_update")
    tbl.execute(
        "UPDATE events SET prev_event_sha256 = ? WHERE seq = 3",
        ("deadbeef" * 16,),
    )
    tbl.commit()
    tbl.close()

    assert log.verify_chain() is False
    with pytest.raises(EventIntegrityError):
        log.replay()
    log.close()


def test_replay_always_verifies_and_halts_on_tamper(tmp_path, clock):
    log = _make_log(tmp_path, clock)
    for i in range(5):
        log.append(_event(payload={"i": i}))

    tbl = sqlite3.connect(str(tmp_path / "log.db"))
    tbl.execute("DROP TRIGGER IF EXISTS events_no_update")
    tbl.execute(
        "UPDATE events SET payload_json = ? WHERE seq = 3",
        (json.dumps({"i": 999}),),
    )
    tbl.commit()
    tbl.close()

    with pytest.raises(EventIntegrityError):
        log.replay()
    log.close()


def test_read_all_events_unchecked_is_tests_only(tmp_path, clock):
    log = _make_log(tmp_path, clock)
    for i in range(5):
        log.append(_event(payload={"i": i}))
    events = log._read_all_events_unchecked()
    assert [e.stream_seq for e in events] == [1, 2, 3, 4, 5]
    log.close()


def test_new_ulid_shape():
    eid = new_ulid(now_ms=1726300000000)
    assert len(eid) == 26
    assert all(c in "0123456789ABCDEFGHJKMNPQRSTVWXYZ" for c in eid)


def test_default_clock_is_system_clock():
    assert isinstance(SystemClock().now_utc_iso(), str)