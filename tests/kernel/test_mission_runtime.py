from __future__ import annotations

"""M3.1 - Persistent Mission Runtime tests (restartable/replayable missions).

Mirrors the helper conventions of `test_mission_lifecycle.py`: a deterministic
`_FixedClock`, an `EventLog` over a tmp db path, and `_append_event()`.  The
process restart is exercised as a REAL boundary seam: a *fresh* `EventLog`
over the SAME db path (never a `reset()` on one object), which is exactly how
`MissionLifecycleOwner.replay/rebuild` is already tested in this suite.

M3.1 guarantees under test:

* Deterministic restart - reopening over the same db with a fresh log +
  mission lifecycle produces a byte-identical `digest()`.
* Idempotent resume - replay/advance over an unchanged log appends nothing;
  `start()`/`complete()` are guarded the same way (no duplicate effects).
* Completion by verification, not claim - a developer/runtime NEVER writes a
  terminal state; "done" is reached only by folding `COMPLETION_EVENT_TYPE`
  ("task.completed") through the mission lifecycle, which *refuses* the
  transition from the wrong state deterministically.
* Replay determinism - the same event history folds to the same state and the
  same digest; integrity is independently auditable via `verify()`.

Nothing in M2.5/M2.4/M2.6 is modified.
"""

import pytest

from jarvis.kernel.done_gate import COMPLETION_EVENT_TYPE
from jarvis.kernel.event_log import (
    Event,
    EventLog,
    SystemClock,
    new_ulid,
)
from jarvis.kernel.mission_lifecycle import (
    MISSION_STARTED,
    MissionLifecycle,
    MissionLifecycleOwner,
)
from jarvis.kernel.mission_runtime import PersistentMissionRuntime

CREATOR_PRINCIPAL_ID = "creator"


# ---------------------------------------------------------------------------
# helpers (mirror test_mission_lifecycle.py)
# ---------------------------------------------------------------------------


class _FixedClock:
    def __init__(self, ts: str) -> None:
        self._ts = ts

    def now_utc_iso(self) -> str:
        return self._ts


def _fixed_clock(ts: str = "2026-09-18T00:00:00.000Z"):
    return _FixedClock(ts)


def _db(tmp_path, name: str = "runtime.db") -> str:
    return str(tmp_path / name)


def _runtime(db: str, *, mission_id: str | None = None) -> PersistentMissionRuntime:
    return PersistentMissionRuntime(
        db_path=db,
        mission_id=mission_id,
        clock=_fixed_clock(),
    )


def _lifecycle_events(runtime: PersistentMissionRuntime) -> list[str]:
    """Persisted mission.* + lifecycle.* event types from the replayed slice
    (via the runtime's own mission-scoped history fold - EventLog.replay()
    is NOT mission-filtered; it takes `since=` only)."""
    return [e.event_type for e in runtime._history()]


# ---------------------------------------------------------------------------
# deterministic restart (no in-memory state crosses the boundary)
# ---------------------------------------------------------------------------


def test_restart_reconstructs_byte_identical_digest(tmp_path):
    """A fresh process over the same db (new EventLog + owner) folds to the
    SAME mission_id, SAME state, SAME digest - determinism across restart."""
    db = _db(tmp_path)

    # process A
    a = _runtime(db, mission_id="m-restart")
    a.start(intent="durable restart")
    a.complete(task_id="task-1")
    digest_a = a.digest()
    id_a = a.mission_id
    a._log.close()

    # process B (fresh EventLog over the same path - the restart seam)
    b = _runtime(db, mission_id=id_a)
    digest_b = b.digest()

    assert b.mission_id == id_a
    assert digest_a == digest_b
    assert len(digest_a) == 64  # sha256 hex


def test_restart_reaches_completed_by_fold_not_claim(tmp_path):
    """Completion after restart is a fold over task.completed - the fold is
    what verifies the transition (deterministic), never a worker claim."""
    db = _db(tmp_path)
    a = _runtime(db, mission_id="m-complete")
    a.start(intent="verify via fold")
    a.complete(task_id="task-9")
    a._log.close()

    b = _runtime(db, mission_id="m-complete")
    state = b.rebuild()

    # deterministic: completed ONLY if task.completed folded through lifecycle
    assert state.state == "completed"
    assert _lifecycle_events(b).count(COMPLETION_EVENT_TYPE) == 1


# ---------------------------------------------------------------------------
# idempotent resume (no duplicated effects)
# ---------------------------------------------------------------------------


def test_replay_repeatedly_appends_nothing(tmp_path):
    """Replaying/advancing a persisted slice that hasn't changed appends
    nothing - resume/replay is idempotent (no effect duplication)."""
    db = _db(tmp_path)
    r = _runtime(db, mission_id="m-idem")
    r.start(intent="idempotent")

    count_after_start = len(list(r._log.replay()))
    _, appended = r._owner.advance()
    assert appended == []
    assert len(list(r._log.replay())) == count_after_start

    _, appended = r._owner.advance()
    assert appended == []


def test_complete_is_guarded_against_duplicate(tmp_path):
    """Appending task.completed twice yields exactly one completion effect."""
    db = _db(tmp_path)
    r = _runtime(db, mission_id="m-guard")
    r.start(intent="guarded complete")
    r.complete(task_id="task-dup")
    r.complete(task_id="task-dup")

    completed = [
        e for e in r._log.replay() if e.event_type == COMPLETION_EVENT_TYPE
    ]
    assert len(completed) == 1


# ---------------------------------------------------------------------------
# completion by verification, not agent claim
# ---------------------------------------------------------------------------


def test_completion_refused_from_wrong_state(tmp_path):
    """Completing before start folds to a deterministic *refusal* - a worker/
    agent can never write a terminal "completed" state directly."""
    db = _db(tmp_path)
    r = _runtime(db, mission_id="m-refuse")

    # attempt completion with no mission.started in the slice
    r.complete(task_id="task-pre")

    state = r.rebuild()
    assert state.state != "completed"
    # the fold refused the transition deterministically
    refused = [
        e for e in r._log.replay() if e.event_type == "task.completion_refused"
    ]
    assert len(refused) == 1


def test_same_history_same_digest_across_two_runtimes(tmp_path):
    """Two runtimes over the same db fold identical state and digest."""
    db = _db(tmp_path)
    a = _runtime(db, mission_id="m-two")
    a.start(intent="two folds")
    a.complete(task_id="task-2")

    b = _runtime(db, mission_id="m-two")

    assert a.rebuild() == b.rebuild()
    assert a.digest() == b.digest()


# ---------------------------------------------------------------------------
# integrity verification is independent and tamper-evident
# ---------------------------------------------------------------------------


def test_verify_chain_integrity(tmp_path):
    """verify(): independent hash-chain integrity check on the persisted log."""
    db = _db(tmp_path)
    r = _runtime(db, mission_id="m-verify")
    r.start(intent="integrity")
    assert r.verify() is True
