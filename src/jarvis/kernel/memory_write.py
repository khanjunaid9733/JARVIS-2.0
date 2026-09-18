from __future__ import annotations

"""Deterministic memory write path (module 10, spec §84.4 / §127.1 / §112).

§84.4 (Memory verification): durable memory writes require verification
proportional to impact. M1 implements only the first rung — the cheap
deterministic checks — via the `memory.write` gate (`DoneGate`). The semantic
verifier and independent verifier for high-impact memory are out of M1 scope.

§127.1 smoke flow: `memory.write.proposed` -> `memory.write.verified` ->
`memory.write.committed`. A memory is promoted to `committed` ONLY when the
gate passes (referenced §112 invariant: "memory promotion requires required
verification"); otherwise `memory.write.rejected` is appended and no memory
is projected.

The writer is deterministic and synchronous: it makes no model calls, no
effects, and no ambient-state reads. Each committed memory's event payload is
folded by `MemoryProjection` (module 7) keyed by the committed event's id.

Disclosed M1 defaults: memory classes are the spec's own set
(provenance/confidence/source/timestamp/validity/retention/supersession are
recorded via `provenance`), and the accepted `memory_class` values are
episodic/semantic/procedural. `content`, `source`, and `confidence` are the
deterministically gated fields.
"""

from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field

from .done_gate import DoneGate, GateDecision
from .event_log import Event, EventLog
from .registry import CREATOR_PRINCIPAL_ID

MEMORY_STREAM_ID = "memory"
MEMORY_PROPOSED = "memory.write.proposed"
MEMORY_VERIFIED = "memory.write.verified"
MEMORY_COMMITTED = "memory.write.committed"
MEMORY_REJECTED = "memory.write.rejected"

MemoryClass = Literal["episodic", "semantic", "procedural"]


class MemoryWriteResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["committed", "rejected"]
    reason: str | None = None
    event_ids: list[str]
    gate: GateDecision


class MemoryWriter:
    """Writes gated memories to the append-only log. Emits four event types:
    proposed, verified, then committed (pass) or rejected (fail)."""

    def __init__(
        self,
        log: EventLog,
        *,
        gate: DoneGate | None = None,
        principal_id: str = CREATOR_PRINCIPAL_ID,
    ) -> None:
        self._log = log
        self._gate = gate or DoneGate()
        self._principal_id = principal_id

    def remember(
        self,
        *,
        content: str,
        source: str,
        confidence: float = 1.0,
        memory_class: MemoryClass = "semantic",
        provenance: Mapping[str, Any] | None = None,
    ) -> MemoryWriteResult:
        record: dict[str, Any] = {
            "content": content,
            "source": source,
            "confidence": confidence,
            "memory_class": memory_class,
            "provenance": dict(provenance or {}),
        }

        event_ids = [self._append(MEMORY_PROPOSED, record)]
        decision = self._gate.evaluate("memory.write", record)
        gate_dump = decision.model_dump()
        event_ids.append(self._append(MEMORY_VERIFIED, {**record, "gate": gate_dump}))

        if not decision.passed:
            event_ids.append(self._append(MEMORY_REJECTED, {**record, "gate": gate_dump}))
            failed = ", ".join(check.name for check in decision.checks if not check.passed)
            return MemoryWriteResult(
                status="rejected",
                reason=f"verification failed: {failed}",
                event_ids=event_ids,
                gate=decision,
            )

        event_ids.append(self._append(MEMORY_COMMITTED, record))
        return MemoryWriteResult(
            status="committed",
            reason=None,
            event_ids=event_ids,
            gate=decision,
        )

    def _append(self, event_type: str, payload: dict[str, Any]) -> str:
        return self._log.append(
            Event(
                stream_id=MEMORY_STREAM_ID,
                event_type=event_type,
                principal_id=self._principal_id,
                payload=payload,
            )
        )
