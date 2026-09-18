from __future__ import annotations

"""Episodic trace tier (M2.1, spec §84.3 / §M2 / §84.4).

Milestone 2 opens the EPISODIC TRACE tier (§84.3): the raw, deterministic
record of what happened, written to the same hash-chained EventLog as M1
memory so that a single replay fold (MemoryIndex, M2.1) can combine committed
memories and episodic traces for recall.

The trace tier reuses the frozen module-10 cheap deterministic gate
(`DoneGate`, kind "memory.write" — the trace record has the same
content/source/confidence evidence shape) so §84.4 verification is
proportional to impact from the first trace. The semantic verifier (M2.4)
is out of scope here.

Determinism and safety mirror module 10: the writer makes no model calls, no
effects, and no ambient-state reads. Caller-declared confidence is clamped to
[0,1] as a schema clamp — that is NOT verification (the spec's verification
ladder is M2.4).

Authority is the disclosed F-C9 default, same as module 10: the writer
performs no principal authority check; authorship is carried as provenance
and on every trace event, and key-based authority lands in M2.8.

M2.1 emits ONE event type per trace (`memory.trace.recorded`) with no
proposed/verified/rejected DFA. On gate failure no event is written and
`TraceWriteResult` carries `status="rejected"`.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .done_gate import DoneGate, GateDecision
from .event_log import Event, EventLog, new_ulid
from .registry import CREATOR_PRINCIPAL_ID

MEMORY_STREAM_ID = "memory"
MEMORY_TRACE_RECORDED = "memory.trace.recorded"
TRACE_KIND_EPISODIC = "episodic"


class TraceWriteResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["recorded", "rejected"]
    reason: str | None = None
    event_id: str | None = None
    gate: GateDecision


class MemoryTraceWriter:
    """Deterministic single-event writer for the episodic trace tier.

    On gate failure the trace is not recorded at all (no event, no fold
    entry) and `reason` names the failing deterministic checks.
    """

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

    def record_episodic(
        self,
        *,
        content: str,
        source: str,
        evidence: list[str] | tuple[str, ...] | None = None,
        confidence: float = 1.0,
        principal_id: str | None = None,
        correlation_id: str | None = None,
    ) -> TraceWriteResult:
        confidence = min(max(float(confidence), 0.0), 1.0)
        evidence = [str(ref) for ref in (evidence or [])]

        record = {
            "content": content,
            "source": source,
            "confidence": confidence,
        }
        decision = self._gate.evaluate("memory.write", record)
        if not decision.passed:
            failed = ", ".join(
                check.name for check in decision.checks if not check.passed
            )
            return TraceWriteResult(
                status="rejected",
                reason=f"trace record rejected: {failed}",
                event_id=None,
                gate=decision,
            )

        event_id = new_ulid()
        self._log.append(
            Event(
                event_id=event_id,
                stream_id=MEMORY_STREAM_ID,
                event_type=MEMORY_TRACE_RECORDED,
                principal_id=principal_id or self._principal_id,
                cause_event_id=evidence[-1] if evidence else None,
                correlation_id=correlation_id or event_id,
                payload={
                    "kind": TRACE_KIND_EPISODIC,
                    "content": content,
                    "source": source,
                    "confidence": confidence,
                    "evidence": evidence,
                },
            )
        )
        return TraceWriteResult(
            status="recorded",
            reason=None,
            event_id=event_id,
            gate=decision,
        )