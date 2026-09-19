from __future__ import annotations

"""Deterministic consolidation pipeline (M2.3, spec §84.3 two-tier).

Two-tier consolidation: episodic trace -> cheap search/index -> consolidation
-> extract -> verify -> contradiction resolution -> promote -> semantic /
procedural memory. «Not every interaction becomes durable semantic memory»
(§84.3, verbatim).

M2.3 is the write-side promotion step: raw `memory.trace.recorded` events
become durable `memory.write.committed` memories — deterministically, in-kernel,
gated by the SAME frozen module-10 `DoneGate`, and decided by a DATA table
(`ConsolidationPolicy`), never by hardcoded branches.

Design invariants (ratified `docs/M2_3_KICKOFF.md` items A-E):
- Hermetic: no model calls (no rerank/embed seam invocation), no effects, no
  ambient-state reads. Synchronous and deterministic: same log + same policy ->
  identical result; ULID ids are promotion OUTCOMES, never inputs.
- Idempotent: a trace is already-consolidated iff its event_id appears in the
  `evidence_ids` provenance of a committed memory; re-running `consolidate()` on
  an unchanged log appends zero events.
- Promotion reuses `MemoryWriter.remember` so the EXACT frozen write path
  (proposed -> verified -> committed) stays authoritative and the `MemoryIndex`
  fold shape is unchanged. Consolidation never mutates or deletes raw traces
  (append-only).
- Only the cheap deterministic rung of the §84.4 ladder runs here; the semantic
  verifier and independent verifier are M2.4.
- Anomaly audit: `memory.consolidate.superseded` (stream "memory") is appended
  ONLY when a contradiction resolves AND `policy.audit` is true. It is folded by
  this module's own projection (never by `MemoryIndex`), so the M2.1 fold and
  digest stay exactly as shipped (FB-M2.2-3 fold-content stability).
"""

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .done_gate import DoneGate, GateDecision
from .event_log import Event, EventLog
from .memory_index import MemoryIndex
from .memory_write import MEMORY_STREAM_ID, MemoryClass, MemoryWriter
from .registry import CREATOR_PRINCIPAL_ID

MEMORY_CONSOLIDATE_SUPERSEDED = "memory.consolidate.superseded"

_WHITESPACE = re.compile(r"\s+")


def _normalize(content: str, mode: Literal["exact", "lower", "fold"]) -> str:
    cleaned = _WHITESPACE.sub(" ", content.strip())
    return cleaned if mode == "exact" else cleaned.lower()


class ExtractRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    normalize: Literal["exact", "lower", "fold"] = "fold"
    content_min_len: int = 8
    evidence_min: int = Field(default=2, ge=1)


class ContradictionRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gate: Literal["same_key_same_source", "disabled"] = "same_key_same_source"
    supersede: bool = True
    supersede_evidence_min: int = Field(default=2, ge=1)


class PromotionRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    memory_class: MemoryClass = "semantic"
    confidence_floor: float = Field(default=0.0, ge=0.0, le=1.0)
    max_promotions: int | None = Field(default=None, ge=1)


class ConsolidationPolicy(BaseModel):
    """The whole decision surface as DATA (kickoff item B).

    Every branch the consolidator takes evaluates one of these fields; there is
    no dispatch on concrete memory identity, model names, or trace contents."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    extract: ExtractRule = Field(default_factory=ExtractRule)
    contradiction: ContradictionRule = Field(default_factory=ContradictionRule)
    promote: PromotionRule = Field(default_factory=PromotionRule)
    audit: bool = True
    principal_id: str = CREATOR_PRINCIPAL_ID


class ConsolidationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    promoted: list[str] = Field(default_factory=list)
    skipped: dict[str, str] = Field(default_factory=dict)
    superseded: dict[str, str] = Field(default_factory=dict)
    counts: dict[str, int] = Field(default_factory=dict)


class MemoryConsolidator:
    """Consolidates raw episodic traces into durable memory (kickoff item A)."""

    def __init__(
        self,
        log: EventLog,
        *,
        policy: ConsolidationPolicy | None = None,
        writer: MemoryWriter | None = None,
        gate: DoneGate | None = None,
        principal_id: str | None = None,
    ) -> None:
        self._log = log
        self._policy = policy or ConsolidationPolicy()
        self._writer = writer or MemoryWriter(
            log, principal_id=principal_id or self._policy.principal_id
        )
        self._gate = gate or DoneGate()

    def consolidate(self) -> ConsolidationResult:
        idx = MemoryIndex.rebuild(self._log)
        policy = self._policy
        promoted_committed: list[str] = []
        skipped: dict[str, str] = {}
        superseded: dict[str, str] = {}

        consumed: set[str] = set()
        for payload in idx.memories.values():
            for evidence_id in (payload.get("provenance") or {}).get(
                "evidence_ids", []
            ):
                consumed.add(evidence_id)
        already_superseded: set[str] = set()
        for event in self._log.replay():
            if event.event_type == MEMORY_CONSOLIDATE_SUPERSEDED:
                old_id = event.payload.get("old_event_id")
                if old_id:
                    already_superseded.add(old_id)

        clusters: dict[tuple[str, str], list[dict[str, Any]]] = {}
        order: list[tuple[str, str]] = []
        for event_id, payload in idx.traces.items():
            if event_id in consumed:
                continue
            content = payload.get("content", "")
            source = payload.get("source", "")
            key = _normalize(str(content), policy.extract.normalize)
            if len(key) < policy.extract.content_min_len:
                skipped[event_id] = "below_content_min_len"
                continue
            cluster_key = (str(source), key)
            if cluster_key not in clusters:
                clusters[cluster_key] = []
                order.append(cluster_key)
            clusters[cluster_key].append(
                {
                    "event_id": event_id,
                    "content": str(content),
                    "source": str(source),
                    "confidence": payload.get("confidence"),
                }
            )

        candidates: list[dict[str, Any]] = []
        for cluster_key in order:
            members = clusters[cluster_key]
            if len(members) < policy.extract.evidence_min:
                for member in members:
                    skipped[member["event_id"]] = "below_evidence_min"
                continue
            candidates.append(
                {
                    "key": cluster_key[1],
                    "source": cluster_key[0],
                    "members": members,
                }
            )

        for candidate in candidates:
            if (
                policy.promote.max_promotions is not None
                and len(promoted_committed) >= policy.promote.max_promotions
            ):
                for member in candidate["members"]:
                    skipped[member["event_id"]] = "promotion_cap"
                continue
            members: list[dict[str, Any]] = candidate["members"]
            numeric = [
                float(m["confidence"])
                for m in members
                if isinstance(m["confidence"], (int, float))
                and not isinstance(m["confidence"], bool)
            ]
            confidence = min(numeric) if numeric else None
            if confidence is None or confidence < policy.promote.confidence_floor:
                for member in members:
                    skipped[member["event_id"]] = "confidence_below_floor"
                continue

            decision: GateDecision = self._gate.evaluate(
                "memory.write",
                {
                    "content": members[-1]["content"],
                    "source": candidate["source"],
                    "confidence": confidence,
                },
            )
            if not decision.passed:
                for member in members:
                    skipped[member["event_id"]] = "verification_failed"
                continue

            match_old: list[str] = []
            if (
                policy.contradiction.gate == "same_key_same_source"
            ):
                for old_id, payload in idx.memories.items():
                    if old_id in already_superseded:
                        continue
                    old_key = _normalize(
                        str(payload.get("content", "")),
                        policy.extract.normalize,
                    )
                    if (
                        str(payload.get("source", "")) == candidate["source"]
                        and old_key == candidate["key"]
                    ):
                        match_old.append(old_id)
                if match_old and not (
                    policy.contradiction.supersede
                    and len(members) >= policy.contradiction.supersede_evidence_min
                ):
                    for member in members:
                        skipped[member["event_id"]] = "collides_with_committed"
                    continue

            result = self._writer.remember(
                content=members[-1]["content"],
                source=candidate["source"],
                confidence=confidence,
                memory_class=policy.promote.memory_class,
                provenance={
                    "evidence_ids": [m["event_id"] for m in members],
                    "superseded": match_old or None,
                },
            )
            if result.status != "committed":
                for member in members:
                    skipped[member["event_id"]] = "promotion_rejected"
                continue
            new_event_id = result.event_ids[-1]
            promoted_committed.append(new_event_id)

            if match_old and policy.audit:
                for old_id in match_old:
                    self._log.append(
                        Event(
                            stream_id=MEMORY_STREAM_ID,
                            event_type=MEMORY_CONSOLIDATE_SUPERSEDED,
                            principal_id=policy.principal_id,
                            cause_event_id=new_event_id,
                            correlation_id=new_event_id,
                            payload={
                                "old_event_id": old_id,
                                "new_event_id": new_event_id,
                                "reason": "same_key_same_source superseded by consolidation",
                                "principal_id": policy.principal_id,
                            },
                        )
                    )
                    superseded[old_id] = new_event_id
                    already_superseded.add(old_id)

        return ConsolidationResult(
            promoted=promoted_committed,
            skipped=skipped,
            superseded=superseded,
            counts={
                "clusters": len(clusters),
                "candidates": len(candidates),
                "promoted": len(promoted_committed),
                "skipped": len(skipped),
                "superseded": len(superseded),
            },
        )