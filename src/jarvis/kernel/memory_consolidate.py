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

Design invariants (ratified `docs/M2_3_KICKOFF.md` items A-E + reconciliation
amendments documented in `docs/M2_3_RECONCILIATION.md`):
- Hermetic: no model calls (no rerank/embed seam invocation), no effects, no
  ambient-state reads. Synchronous and deterministic: same log + same policy ->
  identical result; ULID ids are promotion OUTCOMES, never inputs.
- Idempotent: a trace is already-consolidated iff its event_id appears in the
  `evidence_ids` provenance of any committed memory or in the evidence_ids of a
  `memory.consolidate.rejected` marker (a failed promotion is sticky).
  Re-running `consolidate()` on an unchanged log appends zero events.
- Promotion reuses `MemoryWriter.remember` with the CONSOLIDATOR's own gate
  threaded through, so the frozen write path (proposed -> verified -> committed)
  and the candidate pre-check share one deterministic decision. A rejection is
  recorded once (marker) and never re-attempted. `MemoryIndex` fold shape is
  unchanged; consolidation never mutates or deletes raw traces (append-only).
- Only the cheap deterministic rung of the §84.4 ladder runs here; the semantic
  verifier and independent verifier are M2.4.
- Supersession: `memory.consolidate.superseded` (stream "memory") is appended
  ONLY when a contradiction resolves AND `policy.audit` is true. Bookkeeping on
  later runs is derived from committed provenance (the authoritative record), so
  `audit=False` cannot split-brain. ORIGINAL committed memories (no
  `evidence_ids` provenance) can be superseded when the cluster meets
  `supersede_evidence_min`; CONSOLIDATION-PRODUCT memories are excluded from
  same-key supersession unless `supersede_refine_gap` is set and the candidate's
  aggregate confidence beats them by that margin — a stable fact is promoted
  once and then only refined on a policy-declared confidence gain, never churned.
- The `memory.consolidate.rejected` marker is a DIAGNOSTIC audit event (like
  supersede); it never enters the memories/traces folds. Per the FB-M2.2-3
  precedent the M2.1 digest semantics are "fold-content stable" — ANY appended
  event moves event_count/streams/digest; that is the M2.1 contract, unchanged.
"""

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .done_gate import DoneGate, GateDecision
from .event_log import Event, EventLog
from .memory_trace import MEMORY_TRACE_RECORDED
from .memory_write import (
    MEMORY_COMMITTED,
    MEMORY_STREAM_ID,
    MemoryClass,
    MemoryWriter,
)
from .registry import CREATOR_PRINCIPAL_ID

MEMORY_CONSOLIDATE_SUPERSEDED = "memory.consolidate.superseded"
MEMORY_CONSOLIDATE_REJECTED = "memory.consolidate.rejected"

_WHITESPACE = re.compile(r"\s+")

NormalizeMode = Literal["exact", "lower", "fold"]


def _normalize(content: str, mode: NormalizeMode) -> str:
    """Distinct modes (FB-M2.3-7): exact = strip only (whitespace preserved,
    case preserved); lower = strip + lower (whitespace preserved); fold =
    strip + whitespace-collapse + lower."""
    if mode == "exact":
        return content.strip()
    if mode == "lower":
        return content.strip().lower()
    return _WHITESPACE.sub(" ", content.strip()).lower()


def _id_refs(value: Any) -> list[str]:
    """Robust evidence/superseded reference extraction (FB-M2.3-8): a bare str
    is ONE reference; any other non-sequence shape yields no references (it can
    never crash the consume scan)."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [ref for ref in value if isinstance(ref, str)]
    return []


def _provenance(payload: dict[str, Any]) -> dict[str, Any]:
    prov = payload.get("provenance")
    return prov if isinstance(prov, dict) else {}


def _evidence_refs(payload: dict[str, Any], key: str) -> list[str]:
    return _id_refs(_provenance(payload).get(key))


class ExtractRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    normalize: NormalizeMode = "fold"
    content_min_len: int = 8
    evidence_min: int = Field(default=2, ge=1)


class ContradictionRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gate: Literal["same_key_same_source", "any_key_same_source", "disabled"] = (
        "same_key_same_source"
    )
    supersede: bool = True
    supersede_evidence_min: int = Field(default=2, ge=1)
    supersede_refine_gap: float | None = Field(default=None, ge=0.0, le=1.0)


class PromotionRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    memory_class: MemoryClass = "semantic"
    confidence_floor: float = Field(default=0.0, ge=0.0, le=1.0)
    max_promotions: int | None = Field(default=None, ge=1)
    order: Literal["log", "confidence_desc"] = "log"


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
        # One consolidation, ONE principal (FB-M2.3-1): the constructor-declared
        # caller principal wins over the policy default, and it stamps the write
        # chain AND the audit events.
        self._principal = principal_id or self._policy.principal_id
        self._gate = gate or DoneGate()
        self._writer = writer or MemoryWriter(
            log,
            gate=self._gate,
            principal_id=self._principal,
        )

    def consolidate(self) -> ConsolidationResult:
        policy = self._policy
        events = self._log.replay()

        memories: dict[str, dict[str, Any]] = {}
        traces: dict[str, dict[str, Any]] = {}
        already_superseded: set[str] = set()
        consumed: set[str] = set()

        for event in events:
            if event.event_type == MEMORY_COMMITTED and event.event_id:
                memories[event.event_id] = event.payload
                consumed.update(_evidence_refs(event.payload, "evidence_ids"))
                # Provider bookkeeping is derived from COMMITTED provenance
                # (the authoritative record), not from audit events, so
                # `audit=False` cannot split-brain (FB-M2.3-3): the superseded
                # refs make those memories permanently ineligible as targets.
                already_superseded.update(_evidence_refs(event.payload, "superseded"))
            elif event.event_type == MEMORY_TRACE_RECORDED and event.event_id:
                traces[event.event_id] = event.payload
            elif event.event_type == MEMORY_CONSOLIDATE_SUPERSEDED:
                old_id = event.payload.get("old_event_id")
                if isinstance(old_id, str):
                    already_superseded.add(old_id)
            elif event.event_type == MEMORY_CONSOLIDATE_REJECTED:
                consumed.update(_id_refs(event.payload.get("evidence_ids")))

        skipped: dict[str, str] = {}
        clusters: dict[tuple[str, str], list[dict[str, Any]]] = {}
        order: list[tuple[str, str]] = []
        for event_id, payload in traces.items():
            if event_id in consumed:
                continue
            content = payload.get("content", "")
            key = _normalize(str(content), policy.extract.normalize)
            if len(key) < policy.extract.content_min_len:
                skipped[event_id] = "below_content_min_len"
                continue
            source = str(payload.get("source", ""))
            cluster_key = (source, key)
            if cluster_key not in clusters:
                clusters[cluster_key] = []
                order.append(cluster_key)
            clusters[cluster_key].append(
                {
                    "event_id": event_id,
                    "content": str(content),
                    "source": source,
                    "confidence": payload.get("confidence"),
                }
            )

        def _cluster_confidence(members: list[dict[str, Any]]) -> float | None:
            numeric = [
                float(m["confidence"])
                for m in members
                if isinstance(m["confidence"], (int, float))
                and not isinstance(m["confidence"], bool)
            ]
            return min(numeric) if numeric else None

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
                    "confidence": _cluster_confidence(members),
                }
            )

        if policy.promote.order == "confidence_desc":
            candidates.sort(
                key=lambda c: (
                    c["confidence"] is None,
                    -(c["confidence"] or 0.0),
                    c["members"][0]["event_id"],
                )
            )

        promoted_committed: list[str] = []
        superseded: dict[str, str] = {}

        for candidate in candidates:
            if (
                policy.promote.max_promotions is not None
                and len(promoted_committed) >= policy.promote.max_promotions
            ):
                for member in candidate["members"]:
                    skipped[member["event_id"]] = "promotion_cap"
                continue

            members: list[dict[str, Any]] = candidate["members"]
            confidence = candidate["confidence"]
            if confidence is None or confidence < policy.promote.confidence_floor:
                for member in members:
                    skipped[member["event_id"]] = "confidence_below_floor"
                continue

            if not self._gate.evaluate(
                "memory.write",
                {
                    "content": members[-1]["content"],
                    "source": candidate["source"],
                    "confidence": confidence,
                },
            ).passed:
                for member in members:
                    skipped[member["event_id"]] = "verification_failed"
                continue

            match_old: list[str] = []
            gate = policy.contradiction.gate
            if gate != "disabled":
                for old_id, payload in memories.items():
                    if old_id in already_superseded:
                        continue
                    if _key_matches(
                        payload,
                        candidate,
                        gate,
                        policy.extract.normalize,
                    ):
                        match_old.append(old_id)

            if match_old:
                eligible = [
                    old_id
                    for old_id in match_old
                    if self._can_supersede(
                        old_id,
                        memories[old_id],
                        confidence,
                        len(members),
                        policy,
                    )
                ]
                if not eligible:
                    for member in members:
                        skipped[member["event_id"]] = "collides_with_committed"
                    continue
                match_old = eligible

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
                self._log.append(
                    Event(
                        stream_id=MEMORY_STREAM_ID,
                        event_type=MEMORY_CONSOLIDATE_REJECTED,
                        principal_id=self._principal,
                        correlation_id=members[0]["event_id"],
                        payload={
                            "evidence_ids": [m["event_id"] for m in members],
                            "reason": "promotion rejected by the write gate",
                        },
                    )
                )
                continue

            new_event_id = result.event_ids[-1]
            promoted_committed.append(new_event_id)
            for old_id in match_old:
                superseded[old_id] = new_event_id
                already_superseded.add(old_id)
                if policy.audit:
                    self._log.append(
                        Event(
                            stream_id=MEMORY_STREAM_ID,
                            event_type=MEMORY_CONSOLIDATE_SUPERSEDED,
                            principal_id=self._principal,
                            cause_event_id=new_event_id,
                            correlation_id=new_event_id,
                            payload={
                                "old_event_id": old_id,
                                "new_event_id": new_event_id,
                                "reason": "superseded by consolidation evidence",
                                "principal_id": self._principal,
                            },
                        )
                    )

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

    def _can_supersede(
        self,
        old_id: str,
        payload: dict[str, Any],
        candidate_confidence: float,
        evidence_count: int,
        policy: ConsolidationPolicy,
    ) -> bool:
        if not policy.contradiction.supersede:
            return False
        product = bool(_evidence_refs(payload, "evidence_ids"))
        if product:
            gap = policy.contradiction.supersede_refine_gap
            if gap is None:
                return False
            old_confidence = payload.get("confidence")
            if not isinstance(old_confidence, (int, float)) or isinstance(
                old_confidence, bool
            ):
                return False
            return candidate_confidence - float(old_confidence) >= gap
        return evidence_count >= policy.contradiction.supersede_evidence_min


def _key_matches(
    payload: dict[str, Any],
    candidate: dict[str, Any],
    gate: str,
    mode: NormalizeMode,
) -> bool:
    if str(payload.get("source", "")) != candidate["source"]:
        return False
    if gate == "any_key_same_source":
        return True
    return _normalize(str(payload.get("content", "")), mode) == candidate["key"]