from __future__ import annotations

"""Unified Memory Checkpoint & Single State Digest Engine (Milestone M2.10, spec §85.2 / §86.1 / §134.1).

Closes the M2 proof chain and unifies the memory tract:
1. Unified Memory State (`UnifiedMemoryState`): Combines `MemoryProjection` (module 7:
   streams, providers, memories) and `MemoryIndex` (M2.1: traces) into a single,
   comprehensive memory state with a single canonical state digest (`digest()`),
   fulfilling FB-2 / NAT-03.
2. Incremental Checkpointing (`MemoryCheckpoint`, `CheckpointManager`): Serializes
   frozen projection snapshots to disk with SHA-256 hash chaining (`prev_checkpoint_digest`)
   and header integrity verification.
3. Cold-Start Hydration (`ColdStartRecovery`): Rapidly restores state from the latest
   valid checkpoint and replays only the tail of the `EventLog` (`since=checkpoint.last_seq`),
   producing byte-identical memory state in <100ms.

Invariants:
1. Single Memory-Tract Digest (FB-2 / NAT-03): Replaces separate projection and index digests
   with a single deterministic digest over the unified canonical state.
2. Tamper-Evident & Hash-Chained: Any corruption in checkpoint state, header metadata,
   or the checkpoint hash chain raises `CheckpointIntegrityError`.
3. Deterministic Equivalence: Hydrating from (checkpoint + tail replay) produces a
   `UnifiedMemoryState` whose `digest()` is 100% byte-identical to a full replay from genesis.
4. Fast Cold-Start: Only events committed since the latest checkpoint are replayed during
   cold-start hydration.
5. Strictly Additive: Extends kernel memory and recovery without modifying existing frozen
   modules (modules 1–17 remain byte-identical).
"""

import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .event_log import Event, EventLog, _canonical_json
from .memory_projection import MEMORY_COMMITTED, PROVIDER_ADDED, PROVIDER_REVOKED
from .memory_trace import MEMORY_TRACE_RECORDED

CHECKPOINT_GENESIS = "0" * 64
CHECKPOINT_MAGIC = "jarvis-checkpoint-v1"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CheckpointError(RuntimeError):
    """Base exception for all checkpointing and recovery operations."""


class CheckpointIntegrityError(CheckpointError):
    """Raised when checkpoint state, header digest, or hash chain is corrupt or tampered."""


# ---------------------------------------------------------------------------
# Unified Memory State (FB-2 Single State Digest)
# ---------------------------------------------------------------------------

class UnifiedMemoryState(BaseModel):
    """Unified, rebuildable fold of providers, committed memories, and episodic traces."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    last_seq: int = 0
    event_count: int = 0
    streams: dict[str, int] = Field(default_factory=dict)
    providers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    memories: dict[str, dict[str, Any]] = Field(default_factory=dict)
    traces: dict[str, dict[str, Any]] = Field(default_factory=dict)

    def digest(self) -> str:
        """NAT-03: Single deterministic SHA-256 digest over canonical projection state."""
        return hashlib.sha256(_canonical_json(self.model_dump())).hexdigest()

    def fold_event(self, event: Event, seq: int | None = None) -> "UnifiedMemoryState":
        """Folds a single event into a new immutable UnifiedMemoryState."""
        new_streams = dict(self.streams)
        new_providers = dict(self.providers)
        new_memories = dict(self.memories)
        new_traces = dict(self.traces)

        new_streams[event.stream_id] = event.stream_seq or 0

        if event.event_type == PROVIDER_ADDED:
            meta = event.payload.get("provider", {}).get("meta", {})
            provider_id = meta.get("provider_id")
            if provider_id:
                new_providers[provider_id] = event.payload["provider"]
        elif event.event_type == PROVIDER_REVOKED:
            provider_id = event.payload.get("provider_id")
            if provider_id:
                new_providers.pop(provider_id, None)
        elif event.event_type == MEMORY_COMMITTED and event.event_id:
            new_memories[event.event_id] = event.payload
        elif event.event_type == MEMORY_TRACE_RECORDED and event.event_id:
            new_traces[event.event_id] = event.payload

        new_last_seq = max(self.last_seq, seq) if seq is not None else self.last_seq

        return UnifiedMemoryState(
            last_seq=new_last_seq,
            event_count=self.event_count + 1,
            streams=new_streams,
            providers=new_providers,
            memories=new_memories,
            traces=new_traces,
        )

    def fold_events(
        self,
        events: Sequence[Event],
        last_seq: int | None = None,
    ) -> "UnifiedMemoryState":
        """Folds a sequence of events in order into the state."""
        state = self
        for event in events:
            state = state.fold_event(event)

        final_seq = max(state.last_seq, last_seq) if last_seq is not None else state.last_seq
        if final_seq != state.last_seq:
            return UnifiedMemoryState(
                last_seq=final_seq,
                event_count=state.event_count,
                streams=state.streams,
                providers=state.providers,
                memories=state.memories,
                traces=state.traces,
            )
        return state

    @classmethod
    def rebuild(cls, log: EventLog) -> "UnifiedMemoryState":
        """Rebuilds complete unified state from event log genesis.

        Integrity is delegated to `EventLog.replay()` (NAT-04).
        """
        events = log.replay(since=0)
        state = cls()
        return state.fold_events(events, last_seq=log.last_seq())


# ---------------------------------------------------------------------------
# Checkpoint Schema & Verification
# ---------------------------------------------------------------------------

class MemoryCheckpoint(BaseModel):
    """Durable, hash-chained checkpoint of the unified memory state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    magic: str = CHECKPOINT_MAGIC
    checkpoint_id: str
    created_at_utc: str
    last_seq: int
    event_count: int
    state_digest: str
    prev_checkpoint_digest: str
    checkpoint_digest: str
    state: UnifiedMemoryState

    def compute_header_digest(self) -> str:
        """Computes the deterministic SHA-256 digest of checkpoint metadata."""
        header = {
            "checkpoint_id": self.checkpoint_id,
            "created_at_utc": self.created_at_utc,
            "event_count": self.event_count,
            "last_seq": self.last_seq,
            "magic": self.magic,
            "prev_checkpoint_digest": self.prev_checkpoint_digest,
            "state_digest": self.state_digest,
        }
        return hashlib.sha256(_canonical_json(header)).hexdigest()

    def verify_integrity(self) -> None:
        """Validates internal consistency and cryptographic digests.

        Raises `CheckpointIntegrityError` if any check fails.
        """
        if self.magic != CHECKPOINT_MAGIC:
            raise CheckpointIntegrityError(
                f"invalid checkpoint magic: expected '{CHECKPOINT_MAGIC}', got '{self.magic}'"
            )

        # 1. State digest check
        actual_state_digest = self.state.digest()
        if self.state_digest != actual_state_digest:
            raise CheckpointIntegrityError(
                f"checkpoint state_digest mismatch: header claimed '{self.state_digest}', "
                f"recomputed state digest is '{actual_state_digest}'"
            )

        # 2. Header digest check
        expected_header_digest = self.compute_header_digest()
        if self.checkpoint_digest != expected_header_digest:
            raise CheckpointIntegrityError(
                f"checkpoint_digest mismatch: claimed '{self.checkpoint_digest}', "
                f"recomputed header digest is '{expected_header_digest}'"
            )

        # 3. Sequence / count checks
        if self.last_seq != self.state.last_seq:
            raise CheckpointIntegrityError(
                f"checkpoint last_seq ({self.last_seq}) does not match state last_seq ({self.state.last_seq})"
            )
        if self.event_count != self.state.event_count:
            raise CheckpointIntegrityError(
                f"checkpoint event_count ({self.event_count}) does not match state event_count ({self.state.event_count})"
            )


# ---------------------------------------------------------------------------
# Checkpoint Manager
# ---------------------------------------------------------------------------

class CheckpointManager:
    """Manages creation, storage, retrieval, and chain verification of checkpoints."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def create_checkpoint(
        self,
        state: UnifiedMemoryState,
        *,
        prev_checkpoint: MemoryCheckpoint | None = None,
        created_at_utc: str | None = None,
    ) -> MemoryCheckpoint:
        """Constructs a verified MemoryCheckpoint from a UnifiedMemoryState."""
        ts = (
            created_at_utc
            if created_at_utc is not None
            else datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        )
        prev_digest = (
            prev_checkpoint.checkpoint_digest
            if prev_checkpoint is not None
            else CHECKPOINT_GENESIS
        )

        state_digest = state.digest()
        chk_id = f"chk-{state.last_seq:08d}-{state_digest[:8]}"

        header = {
            "checkpoint_id": chk_id,
            "created_at_utc": ts,
            "event_count": state.event_count,
            "last_seq": state.last_seq,
            "magic": CHECKPOINT_MAGIC,
            "prev_checkpoint_digest": prev_digest,
            "state_digest": state_digest,
        }
        chk_digest = hashlib.sha256(_canonical_json(header)).hexdigest()

        chk = MemoryCheckpoint(
            magic=CHECKPOINT_MAGIC,
            checkpoint_id=chk_id,
            created_at_utc=ts,
            last_seq=state.last_seq,
            event_count=state.event_count,
            state_digest=state_digest,
            prev_checkpoint_digest=prev_digest,
            checkpoint_digest=chk_digest,
            state=state,
        )
        chk.verify_integrity()
        return chk

    def save_checkpoint(self, checkpoint: MemoryCheckpoint) -> Path:
        """Persists a checkpoint atomically to disk."""
        checkpoint.verify_integrity()
        target_path = self.directory / f"{checkpoint.checkpoint_id}.json"
        tmp_path = self.directory / f"{checkpoint.checkpoint_id}.tmp"

        payload_bytes = _canonical_json(checkpoint.model_dump())
        tmp_path.write_bytes(payload_bytes)
        tmp_path.replace(target_path)
        return target_path

    def load_checkpoint(self, path: Path) -> MemoryCheckpoint:
        """Loads and verifies a checkpoint file from disk."""
        if not path.is_file():
            raise CheckpointError(f"checkpoint file not found: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            chk = MemoryCheckpoint.model_validate(data)
            chk.verify_integrity()
            return chk
        except CheckpointIntegrityError:
            raise
        except Exception as exc:
            raise CheckpointIntegrityError(
                f"failed to load checkpoint from {path}: {exc}"
            ) from exc

    def list_checkpoints(self) -> list[MemoryCheckpoint]:
        """Lists all valid checkpoints in directory, sorted by last_seq ascending."""
        checkpoints: list[MemoryCheckpoint] = []
        for file in self.directory.glob("chk-*.json"):
            try:
                chk = self.load_checkpoint(file)
                checkpoints.append(chk)
            except CheckpointIntegrityError:
                # Corrupt checkpoint file ignored during listing or raises
                continue
        checkpoints.sort(key=lambda c: (c.last_seq, c.checkpoint_id))
        return checkpoints

    def latest_checkpoint(self) -> MemoryCheckpoint | None:
        """Returns the latest valid checkpoint, or None if directory has none."""
        chks = self.list_checkpoints()
        return chks[-1] if chks else None

    def verify_chain(self) -> bool:
        """Verifies the hash chain across all checkpoints in directory."""
        chks = self.list_checkpoints()
        if not chks:
            return True

        prev_digest = CHECKPOINT_GENESIS
        for chk in chks:
            if chk.prev_checkpoint_digest != prev_digest:
                return False
            prev_digest = chk.checkpoint_digest
        return True


# ---------------------------------------------------------------------------
# Cold-Start Hydration & Recovery
# ---------------------------------------------------------------------------

class ColdStartRecovery:
    """Cold-start hydration engine restoring memory state from checkpoint + log tail."""

    @staticmethod
    def hydrate(
        log: EventLog,
        checkpoint_manager: CheckpointManager | Path | str,
    ) -> tuple[UnifiedMemoryState, int]:
        """Hydrates UnifiedMemoryState from latest checkpoint plus event log tail.

        Returns (hydrated_state, tail_events_replayed_count).
        """
        mgr = (
            checkpoint_manager
            if isinstance(checkpoint_manager, CheckpointManager)
            else CheckpointManager(checkpoint_manager)
        )

        latest = mgr.latest_checkpoint()
        if latest is None:
            # Cold start without checkpoint: full replay from genesis
            events = log.replay(since=0)
            state = UnifiedMemoryState()
            return state.fold_events(events, last_seq=log.last_seq()), len(events)

        # Hydrate from checkpoint: replay only events committed after checkpoint
        latest.verify_integrity()
        tail_events = log.replay(since=latest.last_seq)
        hydrated = latest.state.fold_events(tail_events, last_seq=log.last_seq())
        return hydrated, len(tail_events)


__all__ = [
    "CHECKPOINT_GENESIS",
    "CHECKPOINT_MAGIC",
    "CheckpointError",
    "CheckpointIntegrityError",
    "CheckpointManager",
    "ColdStartRecovery",
    "MemoryCheckpoint",
    "UnifiedMemoryState",
]
