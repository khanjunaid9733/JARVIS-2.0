from __future__ import annotations

"""Unit tests for M2.10 Unified Memory Checkpoint & Single State Digest (src/jarvis/kernel/checkpoint.py).

Verifies:
1. Unified memory state combining providers, memories, and episodic traces (FB-2 / NAT-03).
2. Single deterministic state digest across the unified memory tract.
3. Durable, hash-chained incremental checkpointing with tamper-evident verification.
4. Cold-start hydration (checkpoint + tail replay) producing byte-identical memory state in <100ms.
5. Fail-closed rejection of tampered checkpoints and broken hash chains.
"""

import time
from pathlib import Path

import pytest

from jarvis.kernel.checkpoint import (
    CHECKPOINT_GENESIS,
    CheckpointIntegrityError,
    CheckpointManager,
    ColdStartRecovery,
    MemoryCheckpoint,
    UnifiedMemoryState,
)
from jarvis.kernel.event_log import Event, EventLog


def _make_event(
    event_type: str,
    stream_id: str,
    payload: dict,
    event_id: str | None = None,
    mission_id: str | None = None,
) -> Event:
    return Event(
        event_id=event_id,
        stream_id=stream_id,
        event_type=event_type,
        principal_id="creator",
        mission_id=mission_id,
        payload=payload,
    )


@pytest.fixture
def event_log(tmp_path: Path) -> EventLog:
    db_path = tmp_path / "events.db"
    return EventLog(db_path)


@pytest.fixture
def checkpoint_dir(tmp_path: Path) -> Path:
    chks = tmp_path / "checkpoints"
    chks.mkdir(parents=True, exist_ok=True)
    return chks


# ---------------------------------------------------------------------------
# Unified Memory State Tests
# ---------------------------------------------------------------------------

def test_unified_memory_state_folding_and_single_digest():
    state = UnifiedMemoryState()
    assert state.last_seq == 0
    assert state.event_count == 0
    initial_digest = state.digest()

    # 1. Fold provider added
    ev1 = _make_event(
        "capability.provider_added",
        "capability",
        {"provider": {"meta": {"provider_id": "model.anthropic"}, "contracts": []}},
        event_id="ev-01",
    )
    state = state.fold_event(ev1, seq=1)
    assert "model.anthropic" in state.providers
    assert state.digest() != initial_digest

    # 2. Fold committed memory
    ev2 = _make_event(
        "memory.write.committed",
        "memory",
        {"key": "user.pref", "val": "dark_mode"},
        event_id="ev-02",
    )
    state = state.fold_event(ev2, seq=2)
    assert "ev-02" in state.memories
    assert state.memories["ev-02"]["val"] == "dark_mode"

    # 3. Fold episodic trace
    ev3 = _make_event(
        "memory.trace.recorded",
        "trace",
        {"summary": "read file X"},
        event_id="ev-03",
    )
    state = state.fold_event(ev3, seq=3)
    assert "ev-03" in state.traces
    assert state.traces["ev-03"]["summary"] == "read file X"

    # 4. Fold provider revoked
    ev4 = _make_event(
        "capability.provider_revoked",
        "capability",
        {"provider_id": "model.anthropic"},
        event_id="ev-04",
    )
    state = state.fold_event(ev4, seq=4)
    assert "model.anthropic" not in state.providers

    assert state.last_seq == 4
    assert state.event_count == 4


def test_unified_memory_state_digest_deterministic():
    ev = _make_event(
        "memory.write.committed",
        "memory",
        {"key": "project.root", "val": "F:\\JARVIS2.0"},
        event_id="ev-root",
    )
    state_a = UnifiedMemoryState().fold_event(ev, seq=1)
    state_b = UnifiedMemoryState().fold_event(ev, seq=1)

    assert state_a.digest() == state_b.digest()


# ---------------------------------------------------------------------------
# Checkpoint Creation & Integrity Verification
# ---------------------------------------------------------------------------

def test_checkpoint_creation_and_verification(checkpoint_dir):
    mgr = CheckpointManager(checkpoint_dir)
    ev = _make_event("memory.write.committed", "memory", {"k": "v"}, event_id="ev-1")
    state = UnifiedMemoryState().fold_event(ev, seq=1)

    chk = mgr.create_checkpoint(state)
    assert chk.prev_checkpoint_digest == CHECKPOINT_GENESIS
    assert chk.state_digest == state.digest()
    assert chk.last_seq == 1
    assert chk.event_count == 1

    chk.verify_integrity()


def test_checkpoint_tampered_state_digest_rejected(checkpoint_dir):
    mgr = CheckpointManager(checkpoint_dir)
    state = UnifiedMemoryState().fold_event(
        _make_event("memory.write.committed", "memory", {"k": "v"}, event_id="e1"),
        seq=1,
    )
    chk = mgr.create_checkpoint(state)

    # Tamper with state digest
    tampered = chk.model_copy(update={"state_digest": "0" * 64})
    with pytest.raises(CheckpointIntegrityError) as exc_info:
        tampered.verify_integrity()
    assert "state_digest mismatch" in str(exc_info.value)


def test_checkpoint_tampered_header_digest_rejected(checkpoint_dir):
    mgr = CheckpointManager(checkpoint_dir)
    state = UnifiedMemoryState().fold_event(
        _make_event("memory.write.committed", "memory", {"k": "v"}, event_id="e1"),
        seq=1,
    )
    chk = mgr.create_checkpoint(state)

    tampered = chk.model_copy(update={"checkpoint_digest": "f" * 64})
    with pytest.raises(CheckpointIntegrityError) as exc_info:
        tampered.verify_integrity()
    assert "checkpoint_digest mismatch" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Checkpoint Hash Chain & Manager Tests
# ---------------------------------------------------------------------------

def test_checkpoint_manager_atomic_save_and_chain(checkpoint_dir):
    mgr = CheckpointManager(checkpoint_dir)

    # Checkpoint 1
    state1 = UnifiedMemoryState().fold_event(
        _make_event("memory.write.committed", "mem", {"item": 1}, event_id="e1"), seq=1
    )
    chk1 = mgr.create_checkpoint(state1)
    mgr.save_checkpoint(chk1)

    # Checkpoint 2 linked to Checkpoint 1
    state2 = state1.fold_event(
        _make_event("memory.write.committed", "mem", {"item": 2}, event_id="e2"), seq=2
    )
    chk2 = mgr.create_checkpoint(state2, prev_checkpoint=chk1)
    mgr.save_checkpoint(chk2)

    assert chk2.prev_checkpoint_digest == chk1.checkpoint_digest

    # Verify chain
    assert mgr.verify_chain() is True
    assert mgr.latest_checkpoint().checkpoint_id == chk2.checkpoint_id
    assert len(mgr.list_checkpoints()) == 2


# ---------------------------------------------------------------------------
# Cold-Start Hydration: Performance (<100ms) & Deterministic Equivalence
# ---------------------------------------------------------------------------

def test_cold_start_hydration_equivalence_and_speed(event_log, checkpoint_dir):
    mgr = CheckpointManager(checkpoint_dir)

    # 1. Append 20 events to event log
    for i in range(1, 21):
        event_log.append(
            Event(
                stream_id="stream-test",
                event_type="memory.write.committed" if i % 2 == 0 else "memory.trace.recorded",
                principal_id="creator",
                payload={"index": i, "data": f"payload-{i}"},
            )
        )

    # 2. Rebuild full state from event log genesis
    full_state = UnifiedMemoryState.rebuild(event_log)
    assert full_state.event_count == 20
    assert full_state.last_seq == 20
    expected_digest = full_state.digest()

    # 3. Snapshot state at event 15
    events_15 = event_log.replay(since=0)[:15]
    state_at_15 = UnifiedMemoryState().fold_events(events_15, last_seq=15)
    chk_15 = mgr.create_checkpoint(state_at_15)
    mgr.save_checkpoint(chk_15)

    # 4. Perform Cold-Start Hydration (checkpoint at 15 + tail replay 16-20)
    start_time = time.perf_counter()
    hydrated_state, tail_count = ColdStartRecovery.hydrate(event_log, mgr)
    duration_ms = (time.perf_counter() - start_time) * 1000

    # Assertions
    assert tail_count == 5  # only events 16, 17, 18, 19, 20 replayed
    assert hydrated_state.event_count == 20
    assert hydrated_state.last_seq == 20
    assert hydrated_state.digest() == expected_digest  # Byte-identical state!

    # Performance requirement: Cold-start recovery <100ms
    assert duration_ms < 100.0, f"Cold-start recovery took {duration_ms:.2f}ms (expected <100ms)"


def test_cold_start_hydration_without_checkpoint_falls_back_to_genesis(event_log, tmp_path):
    # Empty checkpoint directory
    empty_mgr = CheckpointManager(tmp_path / "empty_chks")

    event_log.append(
        Event(
            stream_id="genesis-stream",
            event_type="memory.write.committed",
            principal_id="creator",
            payload={"genesis": True},
        )
    )

    hydrated_state, tail_count = ColdStartRecovery.hydrate(event_log, empty_mgr)
    assert tail_count == 1
    assert hydrated_state.event_count == 1
    assert hydrated_state.last_seq == 1
    assert hydrated_state.digest() == UnifiedMemoryState.rebuild(event_log).digest()
