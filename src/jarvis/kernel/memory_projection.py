from __future__ import annotations

"""Minimal memory projection (module 7, spec §134.1 / §85.2).

A deterministic, rebuildable fold of the hash-chained EventLog into
in-memory projection state. Read-only over the log: it uses
`EventLog.replay()` (which always verifies the chain and halts with
`EventIntegrityError` on tampering — NAT-04) and never reads the events
table directly. It emits no events, makes no model calls, and performs no
effects.

M1 cut (spec §134.1): "minimal memory projection (required by the §127.1
smoke test's `memory.write.*` flow — reconciliation, not scope creep)."

Projection state (deliberately minimal; disclosed):

- `last_seq` / `event_count`: global position of the log at rebuild time.
- `streams`: stream_id -> last stream_seq (spec §85.1: explicit stream
  sequence is authoritative; ULIDs are never a sequence substitute).
- `providers`: `capability.provider_added` / `capability.provider_revoked`
  (F5 writer) folded into provider_id -> canonical `ProviderBinding` dump.
- `memories`: `memory.write.committed` folded into event_id -> event payload.

Ambiguity disclosures (module-7 report):

1. The `memory.write.*` payload schema is NOT specified by the M1 cut and
   no memory writer module exists yet. To avoid inventing a contract, a
   committed memory stores the raw event payload keyed by the event's own
   event_id; when a writer lands this may be refined to typed fields, and
   the digest definition changes with it (documented, not silent).
2. The `Event` model does not carry the global `seq`, so `last_seq` comes
   from the existing `EventLog.last_seq()` accessor (no new EventLog
   method is added, per the module-7 scope restriction).

NAT-03: `digest()` hashes the canonical projection STATE, not the event
bytes, replacing the interim `EventLog.projection_digest()` stream proxy.
"""

import hashlib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .event_log import Event, EventLog, _canonical_json

PROVIDER_ADDED = "capability.provider_added"
PROVIDER_REVOKED = "capability.provider_revoked"
MEMORY_COMMITTED = "memory.write.committed"


class MemoryProjection(BaseModel):
    """Frozen snapshot of M1 projection state (deterministic, rebuildable)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    last_seq: int = 0
    event_count: int = 0
    streams: dict[str, int] = Field(default_factory=dict)
    providers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    memories: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @classmethod
    def rebuild(cls, log: EventLog) -> "MemoryProjection":
        """Rebuild projection state from the log.

        Integrity is delegated to `EventLog.replay()`: a tampered log raises
        `EventIntegrityError`, which this method deliberately does NOT catch.
        """
        events = log.replay()
        return cls._from_events(events, last_seq=log.last_seq())

    @classmethod
    def _from_events(
        cls, events: list[Event], last_seq: int
    ) -> "MemoryProjection":
        streams: dict[str, int] = {}
        providers: dict[str, dict[str, Any]] = {}
        memories: dict[str, dict[str, Any]] = {}
        for event in events:
            # replay() returns global order; last write per stream wins.
            streams[event.stream_id] = event.stream_seq or 0
            if event.event_type == PROVIDER_ADDED:
                meta = event.payload.get("provider", {}).get("meta", {})
                provider_id = meta.get("provider_id")
                if provider_id:
                    providers[provider_id] = event.payload["provider"]
            elif event.event_type == PROVIDER_REVOKED:
                provider_id = event.payload.get("provider_id")
                if provider_id:
                    providers.pop(provider_id, None)
            elif event.event_type == MEMORY_COMMITTED and event.event_id:
                memories[event.event_id] = event.payload
        return cls(
            last_seq=last_seq,
            event_count=len(events),
            streams=streams,
            providers=providers,
            memories=memories,
        )

    def digest(self) -> str:
        """NAT-03: deterministic digest over canonical projection STATE.

        Excludes event bytes, timestamps, and ULIDs (except memory keys,
        which are event ids) so identical event sequences produce identical
        digests regardless of clock or storage identity.
        """
        return hashlib.sha256(_canonical_json(self.model_dump())).hexdigest()

    def provider_ids(self) -> list[str]:
        """Registered provider ids in the projection, sorted for stability."""
        return sorted(self.providers)