# M5.3 — Distributed Event Log Replication & Peer Sync (Kickoff & Design Contract)

**Status:** ACCEPTED DESIGN — architectural contract for implementation.  
**Author/owner:** Antigravity (Gemini) designs & verifies; Big Pickle (OpenCode) implements.  
**Milestone:** Phase 4: M5 (Embodiment & External Device Nodes), package M5.3.  
**Baseline:** `task/supervisor @ e2ac1c2`, **835 passed in 260s**, 0 failed.  
**Proof Target (M5.3):** `export sync batch -> vector clock check -> peer transport -> cryptographically verify -> append-only ingest -> digest stability`.

---

## 1. Why This Exists

In Milestone M5.2, JARVIS established secure pairing, capability manifests, and authenticated RPC dispatch to external companion bodies (phones, robotic nodes, sensor hubs).

However, external nodes generate independent state and telemetry (e.g. sensor readings, battery status, camera frames, node health events). Furthermore, when disconnected from the central hub, companion nodes must record local events to their own local append-only event log.

When connection is re-established (or continuously over streaming RPC), these event logs must synchronize:
1. **Append-Only Ledger Integrity (Invariant I6)**: No distributed sync may ever mutate, rewrite, or delete past events in either peer's ledger.
2. **Deterministic Cryptographic Verification**: Synced events must retain their physical provenance, payload hashes, and original ULID `event_id`s. Any tampering or corrupted byte halts replication immediately (`EventIntegrityError`).
3. **Causal Ordering via Vector Clocks**: Events across nodes must be causally ordered without relying on perfectly synchronized wall clocks.
4. **Conflict Detection & Fail-Closed Protection**: If two nodes claim contradictory history or duplicate `event_id`s with differing hashes, the sync engine refuses to silently overwrite, raising a `ReplicationConflictError`.

---

## 2. Grounding in Existing Modules

- **`src/jarvis/kernel/event_log.py`**: `Event`, `EventLog`, `EventIntegrityError`, hash chaining (`event_sha256`, `prev_event_sha256`, `payload_sha256`).
- **`src/jarvis/kernel/memory_projection.py`**: `MemoryProjection.digest()` deterministic fold over events.
- **`src/jarvis/nodes/protocol.py`**: `NodeSpec`, `RPCRequest`, `RPCResponse`, `NodeTransport`.
- **`src/jarvis/nodes/rpc_adapter.py`**: `NodeManager` authenticated transport.

---

## 3. Detailed Design Contract

### A. Data Structures (`src/jarvis/kernel/sync/replication.py`)

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence
from jarvis.kernel.event_log import Event

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
```

### B. Replication Engine Interface

```python
class ReplicationEngine:
    def __init__(self, event_log: EventLog, local_node_id: str) -> None:
        self.log = event_log
        self.local_node_id = local_node_id

    def export_batch(
        self,
        target_node_id: str,
        since_stream_seqs: Mapping[str, int] | None = None,
        limit: int = 200,
    ) -> SyncBatch:
        """Export up to `limit` events newer than `since_stream_seqs`."""
        ...

    def ingest_batch(self, batch: SyncBatch) -> SyncSummary:
        """Ingest incoming batch with strict cryptographic integrity & idempotency.
        
        Rules:
        1. If event_id already exists with identical event_sha256, skip (idempotent).
        2. If event_id exists with different payload or hash, raise ReplicationConflictError.
        3. Verify event.compute_payload_sha256() == event.payload_sha256.
        4. Append valid new events to the local EventLog in stream_seq order.
        """
        ...
```

---

## 4. Test Suite Requirements (`tests/kernel/test_log_sync.py`)

1. **`test_export_batch_filters_by_watermark`**: Only events past stream watermark are exported.
2. **`test_ingest_batch_appends_cleanly`**: Ingesting foreign events appends to local EventLog with new local seq and valid hash chaining.
3. **`test_ingest_batch_is_idempotent`**: Re-ingesting the exact same batch skips events cleanly without error (`applied_count=0, skipped_count=N`).
4. **`test_tampered_payload_in_batch_raises_integrity_error`**: Mismatched `payload_sha256` triggers immediate fail-closed rejection.
5. **`test_conflicting_event_id_raises_replication_conflict_error`**: Duplicate `event_id` with contradictory payload fails closed.
6. **`test_vector_clock_monotonicity`**: VectorClock increments correctly and correctly evaluates causal precedence.
7. **`test_bidirectional_sync_reaches_consensus`**: Hub and Node both exchange local events and reach identical projection states.
8. **`test_rpc_sync_roundtrip`**: In-memory `NodeManager` RPC call `node.sync_events` successfully pulls and applies events across nodes.

---

## 5. Work Division

1. **Antigravity (Chief Architect)**:
   - Formulates design contract and publishes `docs/M5_3_KICKOFF.md`.
   - Creates directory `src/jarvis/kernel/sync/`.
2. **OpenCode (Hands-on Builder)**:
   - Implements `src/jarvis/kernel/sync/replication.py`.
   - Implements `tests/kernel/test_log_sync.py`.
3. **Antigravity (Quality Reviewer & Verifier)**:
   - Audits code quality, executes test suite, verifies 0 regressions across all 835 baseline tests.
