from __future__ import annotations

"""M3.1 - Persistent Mission Runtime.

A mission as a *durable, restartable runtime* over one hash-chained
`EventLog`.  The event log is the single source of truth; mission state is
NEVER a second store - it is always a deterministic fold over the
mission's persisted slice (via `MissionLifecycleOwner.rebuild()`).

Guarantees (see tests/kernel/test_mission_runtime.py):

* Deterministic restart - a fresh `EventLog`/`MissionLifecycleOwner` opened
  over the same db path reconstructs a byte-identical `digest()`.
* Idempotent resume - replaying/advancing over an unchanged log appends
  nothing (no duplicated effects).  `start()`/`complete()` are guarded the
  same way.
* Completion by verification, not agent claim - "done" is reached only by
  folding `COMPLETION_EVENT_TYPE` ("task.completed") through the mission
  lifecycle; the fold *refuses* to reach terminal "completed" from the
  wrong state (deterministic transition rules).  A worker/agent can never
  write a terminal state directly.
* Replay determinism - the same event history yields the same fold and the
  same digest; integrity is independently auditable via `verify()`.
*/"
"""

import hashlib
import json
from typing import Any

from jarvis.kernel.done_gate import (
    COMPLETION_EVENT_TYPE,
    COMPLETION_REFUSED_EVENT_TYPE,
)
from jarvis.kernel.event_log import Event, EventLog, SystemClock, new_ulid
from jarvis.kernel.mission_lifecycle import (
    MISSION_STARTED,
    MISSION_STREAM_ID,
    MissionLifecycle,
    MissionLifecycleOwner,
)


def _canonical_json(value: Any) -> bytes:
    """Stable, key-sorted JSON for deterministic digests (sort_keys;
    separators pinned so bytes are identical across processes)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class PersistentMissionRuntime:
    """Durable mission runtime rooted on one `EventLog` path.

    The runtime never holds durable mission state of its own; callers must
    rebuild from `rebuild()` rather than trusting in-memory fields after a
    process boundary.
    */"
    """

    def __init__(
        self,
        db_path: str,
        *,
        mission_id: str | None = None,
        clock: Any | None = None,
        principal_id: str = "creator",
    ) -> None:
        self._db_path = db_path
        self._log = EventLog(db_path=db_path, clock=clock or SystemClock())
        self._principal_id = principal_id
        id_part = new_ulid()
        self._mission_id = mission_id or f"mission-{id_part}"
        self._owner = MissionLifecycleOwner(self._log, mission_id=self._mission_id)

    # -- identity ---------------------------------------------------------

    @property
    def mission_id(self) -> str:
        return self._mission_id

    @property
    def log(self) -> EventLog:
        return self._log

    @property
    def db_path(self) -> str:
        return self._db_path

    # -- lifecycle operations (all idempotent, event-sourced) --------------

    def start(self, *, intent: str, task_id: str | None = None) -> str:
        """Persist mission.started once, then fold it through the lifecycle so
        the persisted slice is CURRENT immediately - a later resume()/advance()
        over an unchanged log appends NOTHING (idempotent, deterministic fold)."""
        if not any(
            e.event_type == MISSION_STARTED for e in self._history()
        ):
            self._append(
                event_type=MISSION_STARTED,
                payload={"intent": intent},
                task_id=task_id,
            )
        self._owner.advance()
        return self._mission_id

    def rebuild(self) -> MissionLifecycle:
        """Read-only deterministic fold: state from the persisted slice alone."""
        return self._owner.rebuild()

    def resume(self) -> tuple[MissionLifecycle, list[str]]:
        """Idempotent fold + missing lifecycle appends (no-op on unchanged log)."""
        return self._owner.advance()

    def complete(
        self,
        *,
        task_id: str,
        principal_id: str = "creator",
    ) -> MissionLifecycle:
        """Completion by verification, not agent claim: fold *refuses* a
        completion attempted before the mission is started (never a bare
        "completed" from the wrong state).  A started mission appends
        task.completed exactly once and the lifecycle accepts the fold."""
        if not any(
            e.event_type == MISSION_STARTED for e in self._history()
        ):
            already_refused = any(
                e.event_type == COMPLETION_REFUSED_EVENT_TYPE
                and e.task_id == task_id
                for e in self._history()
            )
            if not already_refused:
                self._append(
                    event_type=COMPLETION_REFUSED_EVENT_TYPE,
                    task_id=task_id,
                    payload={"task_id": task_id},
                    principal_id=principal_id,
                )
            state, _ = self._owner.advance()
            return state

        already = any(
            e.event_type == COMPLETION_EVENT_TYPE and e.task_id == task_id
            for e in self._history()
        )
        if not already:
            self._append(
                event_type=COMPLETION_EVENT_TYPE,
                task_id=task_id,
                payload={"task_id": task_id},
                principal_id=principal_id,
            )
        state, _ = self._owner.advance()
        return state

    # -- verification / integrity ------------------------------------------

    def verify(self) -> bool:
        """Independent hash-chain integrity check (auth chain, tamper-evident)."""
        return self._log.verify_chain()

    def digest(self, state: MissionLifecycle | None = None) -> str:
        """Deterministic state digest - equal across processes for equal history."""
        st = state if state is not None else self.rebuild()
        payload = _canonical_json(st.model_dump(mode="json"))
        return hashlib.sha256(payload).hexdigest()

    # -- internals -----------------------------------------------------------

    def _append(
        self,
        *,
        event_type: str,
        principal_id: str | None = None,
        task_id: str | None = None,
        payload: dict | None = None,
    ) -> str:
        return self._log.append(
            Event(
                event_id=new_ulid(),
                stream_id=MISSION_STREAM_ID,
                event_type=event_type,
                principal_id=principal_id or self._principal_id,
                mission_id=self._mission_id,
                task_id=task_id,
                correlation_id=self._mission_id,
                payload=dict(payload or {}),
            )
        )

    def _history(self) -> list[Event]:
        """Persisted mission slice (idempotent; the only history the runtime
        ever folds - matches MissionLifecycleOwner.replay() semantics)."""
        return [e for e in self._log.replay() if e.mission_id == self._mission_id]
