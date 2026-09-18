from __future__ import annotations

"""MemoryIndex: M2.1 combined projection of committed memories + episodic
traces (spec §84.3 two-tier consolidation, tier 1).

Additive to module 7: `MemoryIndex` is a NEW projection; `MemoryProjection`
is untouched (modules 1-17 frozen). `MemoryIndex` folds the same
`memory.write.committed` payloads keyed by event_id that module 7 does AND
`memory.trace.recorded` into a second dict. Both are consumed by the M2.1
`Memory` API for combined recall.

Quality bar mirrors module 7: `rebuild()` delegates integrity to
`EventLog.replay()` (NAT-04 halts on tampering; it never reads the events
table directly). It emits no events, makes no model calls, and performs no
effects.

NAT-03 digest over the canonical projection STATE, matching module-7
semantics: ULID event-ids are fold keys (and trace evidence may reference
external event ids), so digest equality is per-log rebuild — identical replay
yields an identical digest; cross-run digests are not promised.
"""

import hashlib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .event_log import Event, EventLog, _canonical_json
from .memory_projection import MEMORY_COMMITTED
from .memory_trace import MEMORY_TRACE_RECORDED


class MemoryIndex(BaseModel):
    """Frozen, rebuildable fold of committed memories and episodic traces."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    last_seq: int = 0
    event_count: int = 0
    streams: dict[str, int] = Field(default_factory=dict)
    memories: dict[str, dict[str, Any]] = Field(default_factory=dict)
    traces: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @classmethod
    def rebuild(cls, log: EventLog) -> "MemoryIndex":
        events = log.replay()
        return cls._from_events(events, last_seq=log.last_seq())

    @classmethod
    def _from_events(
        cls, events: list[Event], last_seq: int
    ) -> "MemoryIndex":
        streams: dict[str, int] = {}
        memories: dict[str, dict[str, Any]] = {}
        traces: dict[str, dict[str, Any]] = {}
        for event in events:
            streams[event.stream_id] = event.stream_seq or 0
            if event.event_type == MEMORY_COMMITTED and event.event_id:
                memories[event.event_id] = event.payload
            elif event.event_type == MEMORY_TRACE_RECORDED and event.event_id:
                traces[event.event_id] = event.payload
        return cls(
            last_seq=last_seq,
            event_count=len(events),
            streams=streams,
            memories=memories,
            traces=traces,
        )

    def digest(self) -> str:
        """NAT-03: deterministic digest over canonical projection STATE."""
        return hashlib.sha256(_canonical_json(self.model_dump())).hexdigest()