from __future__ import annotations

"""Module 7 minimal memory projection tests (spec §134.1 / §85.2).

Deterministic, rebuildable fold of the hash-chained EventLog. Read-only:
no event emission, no model calls, no effects. NAT-03 moves from the
interim stream-digest proxy to a digest over projection state.
"""

import json
import sqlite3

import pytest

from jarvis.kernel.event_log import Event, EventIntegrityError, EventLog
from jarvis.kernel.memory_projection import MEMORY_COMMITTED, MemoryProjection
from jarvis.kernel.registry import (
    CREATOR_PRINCIPAL_ID,
    CapabilityRegistry,
    ProviderBinding,
)

SEEDED_PROVIDER_IDS = [
    "fs.default",
    "terminal.default",
    "model.adapter",
    "http.default",
]


class _FixedClock:
    def __init__(self, ts: str) -> None:
        self._ts = ts

    def now_utc_iso(self) -> str:
        return self._ts


def _log(tmp_path, name: str = "log.db", ts: str = "2026-09-18T00:00:00.000Z") -> EventLog:
    return EventLog(db_path=str(tmp_path / name), clock=_FixedClock(ts))


def _note(event_type: str, stream_id: str = "memory", **payload) -> Event:
    return Event(
        stream_id=stream_id,
        event_type=event_type,
        principal_id=CREATOR_PRINCIPAL_ID,
        payload=payload,
    )


# ---------------------------------------------------------------------------
# Empty / determinism
# ---------------------------------------------------------------------------

def test_empty_log_yields_empty_projection_and_stable_digest(tmp_path):
    log = _log(tmp_path)

    projection = MemoryProjection.rebuild(log)

    assert projection.last_seq == 0
    assert projection.event_count == 0
    assert projection.streams == {}
    assert projection.providers == {}
    assert projection.memories == {}
    assert projection.digest() == MemoryProjection().digest()
    assert MemoryProjection.rebuild(log).digest() == projection.digest()


def test_rebuild_is_deterministic_same_digest_twice(tmp_path):
    log = _log(tmp_path)
    for i in range(5):
        log.append(_note("memory.write.committed", content=f"m{i}"))

    first = MemoryProjection.rebuild(log)
    second = MemoryProjection.rebuild(log)

    assert first == second
    assert first.digest() == second.digest()


def test_adding_events_changes_digest_and_rebuild_reproduces_it(tmp_path):
    log = _log(tmp_path)
    log.append(_note("memory.write.committed", content="one"))
    before = MemoryProjection.rebuild(log).digest()

    log.append(_note("memory.write.committed", content="two"))
    after = MemoryProjection.rebuild(log).digest()
    assert before != after

    # rebuilding the same (identical) log reproduces the digest
    assert MemoryProjection.rebuild(log).digest() == after


def test_state_digest_is_clock_independent(tmp_path):
    """Projection state excludes timestamps, so different clocks agree."""
    early = _log(tmp_path, name="early.db", ts="2020-01-01T00:00:00.000Z")
    late = _log(tmp_path, name="late.db", ts="2031-12-31T23:59:59.000Z")
    for log in (early, late):
        CapabilityRegistry.seed_m1_defaults(log=log)

    assert MemoryProjection.rebuild(early).digest() == MemoryProjection.rebuild(
        late
    ).digest()


# ---------------------------------------------------------------------------
# Capability projection (consumes the F5 writer)
# ---------------------------------------------------------------------------

def test_capability_events_reconstruct_seeded_provider_set(tmp_path):
    log = _log(tmp_path)
    registry = CapabilityRegistry.seed_m1_defaults(log=log)

    projection = MemoryProjection.rebuild(log)

    assert projection.provider_ids() == sorted(SEEDED_PROVIDER_IDS)
    for provider_id in SEEDED_PROVIDER_IDS:
        reconstructed = ProviderBinding.model_validate(
            projection.providers[provider_id]
        )
        assert reconstructed == registry.get_provider(provider_id)


def test_revoked_provider_is_absent_from_projection(tmp_path):
    log = _log(tmp_path)
    registry = CapabilityRegistry.seed_m1_defaults(log=log)

    registry.revoke_provider("http.default", CREATOR_PRINCIPAL_ID)

    projection = MemoryProjection.rebuild(log)
    assert projection.provider_ids() == [
        "fs.default",
        "model.adapter",
        "terminal.default",
    ]
    assert "http.default" not in projection.providers


def test_projection_without_capability_events_has_no_providers(tmp_path):
    log = _log(tmp_path)
    log.append(_note("memory.write.committed", content="x"))

    assert MemoryProjection.rebuild(log).providers == {}


# ---------------------------------------------------------------------------
# Minimal memory projection (memory.write.* flow, §127.1 / §134.1)
# ---------------------------------------------------------------------------

def test_memory_write_committed_is_projected(tmp_path):
    log = _log(tmp_path)
    event_id = log.append(
        _note("memory.write.committed", content="the safe word is umbrella")
    )

    projection = MemoryProjection.rebuild(log)

    assert set(projection.memories) == {event_id}
    assert projection.memories[event_id] == {
        "content": "the safe word is umbrella"
    }
    # proposed/verified must not be projected as committed memories
    log.append(_note("memory.write.proposed", content="ignored"))
    log.append(_note("memory.write.verified", content="ignored"))
    assert set(MemoryProjection.rebuild(log).memories) == {event_id}


# ---------------------------------------------------------------------------
# Integrity (NAT-04 delegation)
# ---------------------------------------------------------------------------

def test_tampered_log_halts_projection(tmp_path):
    log = _log(tmp_path)
    log.append(_note("memory.write.committed", content="safe"))
    log.append(_note("memory.write.committed", content="target"))
    assert log.verify_chain() is True

    tbl = sqlite3.connect(str(tmp_path / "log.db"))
    tbl.execute("DROP TRIGGER IF EXISTS events_no_update")
    tbl.execute(
        "UPDATE events SET payload_json = ? WHERE seq = 2",
        (json.dumps({"content": "tampered"}),),
    )
    tbl.commit()
    tbl.close()

    with pytest.raises(EventIntegrityError):
        MemoryProjection.rebuild(log)


# ---------------------------------------------------------------------------
# NAT-03: state digest replaces the interim stream digest
# ---------------------------------------------------------------------------

def test_nat_03_state_digest_differs_from_interim_stream_digest(tmp_path):
    log = _log(tmp_path)
    registry = CapabilityRegistry.seed_m1_defaults(log=log)
    registry.revoke_provider("terminal.default", CREATOR_PRINCIPAL_ID)
    log.append(_note("memory.write.committed", content="x"))

    state_digest = MemoryProjection.rebuild(log).digest()

    assert log.last_seq() == 6
    assert state_digest != log.projection_digest()  # replacement is real


def test_nat_03_replay_identical_projection_twice(tmp_path):
    log = _log(tmp_path)
    CapabilityRegistry.seed_m1_defaults(log=log)

    assert MemoryProjection.rebuild(log).digest() == MemoryProjection.rebuild(
        log
    ).digest()