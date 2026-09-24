from __future__ import annotations

"""Distributed Event Log Replication and Peer Synchronization (src/jarvis/kernel/sync/replication.py).

Enforces Invariant I6: Append-only ledger integrity without silent history mutation.
Provides vector clock causality tracking, cryptographic hash verification, and idempotent sync.
"""

from dataclasses import dataclass, field
import json
import uuid
from typing import Any, Mapping, Sequence

from jarvis.kernel.event_log import (
    Event,
    EventIntegrityError,
    EventLog,
    _canonical_json,
    _sha256,
)


class ReplicationError(RuntimeError):
    """Base error for distributed event log replication."""


class ReplicationConflictError(ReplicationError):
    """Raised when an incoming event contradicts existing immutable ledger state."""


@dataclass(frozen=True)
class VectorClock:
    """Monotonic vector clock mapping node_id -> sequence number."""

    clock: Mapping[str, int] = field(default_factory=dict)

    def get(self, node_id: str) -> int:
        return self.clock.get(node_id, 0)

    def increment(self, node_id: str, seq: int | None = None) -> VectorClock:
        new_clock = dict(self.clock)
        new_clock[node_id] = seq if seq is not None else (new_clock.get(node_id, 0) + 1)
        return VectorClock(clock=new_clock)

    def is_causally_newer(self, other: VectorClock) -> bool:
        """Return True if self has observed all events of other and at least one strictly newer."""
        has_strictly_greater = False
        all_nodes = set(self.clock.keys()) | set(other.clock.keys())
        for nid in all_nodes:
            s_val = self.get(nid)
            o_val = other.get(nid)
            if s_val < o_val:
                return False
            if s_val > o_val:
                has_strictly_greater = True
        return has_strictly_greater

    def merge(self, other: VectorClock) -> VectorClock:
        """Combine two vector clocks by taking the component-wise maximum."""
        all_nodes = set(self.clock.keys()) | set(other.clock.keys())
        merged = {nid: max(self.get(nid), other.get(nid)) for nid in all_nodes}
        return VectorClock(clock=merged)


@dataclass(frozen=True)
class SyncBatch:
    """A batch of events transferred during replication."""

    batch_id: str
    source_node_id: str
    target_node_id: str
    events: tuple[Event, ...]
    vector_clock: VectorClock
    stream_watermarks: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class SyncSummary:
    """Deterministic result summary of a replication sync run."""

    batch_id: str
    applied_count: int
    skipped_count: int
    conflicts: tuple[str, ...] = ()
    new_vector_clock: VectorClock = field(default_factory=VectorClock)


class ReplicationEngine:
    """Distributed event log replication engine preserving Invariant I6 (no silent mutation)."""

    def __init__(self, event_log: EventLog, local_node_id: str) -> None:
        self.log = event_log
        self.local_node_id = local_node_id
        self._vector_clock = VectorClock(clock={local_node_id: 0})

    @property
    def vector_clock(self) -> VectorClock:
        """Return current vector clock stamped with local event log sequence."""
        cur = self.log._conn.execute("SELECT COALESCE(MAX(seq), 0) AS max_seq FROM events")
        max_seq = int(cur.fetchone()["max_seq"])
        return self._vector_clock.increment(self.local_node_id, max_seq)

    def get_watermarks(self) -> dict[str, int]:
        """Return highest stream_seq for each stream in the local log."""
        cur = self.log._conn.execute(
            "SELECT stream_id, MAX(stream_seq) AS max_stream_seq FROM events GROUP BY stream_id"
        )
        return {row["stream_id"]: int(row["max_stream_seq"]) for row in cur.fetchall()}

    def export_batch(
        self,
        target_node_id: str,
        since_stream_seqs: Mapping[str, int] | None = None,
        limit: int = 200,
    ) -> SyncBatch:
        """Export up to `limit` events newer than `since_stream_seqs`."""
        watermarks = since_stream_seqs or {}
        cur = self.log._conn.execute("SELECT * FROM events ORDER BY seq ASC")
        rows = cur.fetchall()
        exported_events: list[Event] = []
        new_watermarks: dict[str, int] = dict(watermarks)

        for row in rows:
            sid = row["stream_id"]
            sseq = int(row["stream_seq"])
            last_known = watermarks.get(sid, 0)
            if sseq > last_known:
                ev = Event(
                    event_id=row["event_id"],
                    stream_id=row["stream_id"],
                    stream_seq=row["stream_seq"],
                    ts_utc=row["ts_utc"],
                    event_type=row["event_type"],
                    schema_version=row["schema_version"],
                    principal_id=row["principal_id"],
                    mission_id=row["mission_id"],
                    task_id=row["task_id"],
                    cause_event_id=row["cause_event_id"],
                    correlation_id=row["correlation_id"],
                    payload=json.loads(row["payload_json"]),
                    actor_model=row["actor_model"],
                    payload_sha256=row["payload_sha256"],
                    prev_event_sha256=row["prev_event_sha256"],
                    event_sha256=row["event_sha256"],
                )
                exported_events.append(ev)
                new_watermarks[sid] = max(new_watermarks.get(sid, 0), sseq)
                if len(exported_events) >= limit:
                    break

        batch_id = str(uuid.uuid4())
        return SyncBatch(
            batch_id=batch_id,
            source_node_id=self.local_node_id,
            target_node_id=target_node_id,
            events=tuple(exported_events),
            vector_clock=self.vector_clock,
            stream_watermarks=new_watermarks,
        )

    def ingest_batch(self, batch: SyncBatch) -> SyncSummary:
        """Ingest incoming batch with strict cryptographic integrity & idempotency.

        Rules:
        1. Verify payload_sha256 integrity: compute_payload_sha256() == event.payload_sha256.
           If mismatched, raise EventIntegrityError.
        2. Check for duplicate event_id:
           - If identical payload: skip (idempotent duplicate).
           - If differing payload: raise ReplicationConflictError (fail-closed, no silent mutation).
        3. Append valid events into local event log.
        4. Advance vector clock.
        """
        applied = 0
        skipped = 0
        conflicts: list[str] = []

        for ev in batch.events:
            # 1. Cryptographic payload check
            computed_payload_sha = ev.compute_payload_sha256()
            if ev.payload_sha256 is not None and computed_payload_sha != ev.payload_sha256:
                raise EventIntegrityError(
                    f"Replicated event {ev.event_id} payload hash mismatch: "
                    f"claimed {ev.payload_sha256} != computed {computed_payload_sha}"
                )

            # 2. Check if event_id already exists in local DB
            cur = self.log._conn.execute(
                "SELECT event_id, payload_json, payload_sha256 FROM events WHERE event_id = ?",
                (ev.event_id,),
            )
            existing = cur.fetchone()
            if existing:
                existing_payload = json.loads(existing["payload_json"])
                if existing_payload == ev.payload:
                    skipped += 1
                    continue
                else:
                    err_msg = (
                        f"Conflict on event {ev.event_id}: existing payload differs from replicated payload."
                    )
                    conflicts.append(err_msg)
                    raise ReplicationConflictError(err_msg)

            # 3. New event: append to local EventLog (preserves original event_id)
            self.log.append(ev)
            applied += 1

        self._vector_clock = self._vector_clock.merge(batch.vector_clock)

        return SyncSummary(
            batch_id=batch.batch_id,
            applied_count=applied,
            skipped_count=skipped,
            conflicts=tuple(conflicts),
            new_vector_clock=self.vector_clock,
        )