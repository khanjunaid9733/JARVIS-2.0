from __future__ import annotations

"""Freebuff M2.3 red-team evidence probes - branch `task/m2.3` @ `c78f406`.

These are EVIDENCE, not accepted architecture (Freebuff role contract). Each
test PINS the behavior observed on disk and names, in a comment, the behavior
the finding recommends. Assertions marked ``# FLIPS ON FIX`` are the ones that
change when (and only when) the corresponding reconciliation lands; the rest
are regression pins for behavior considered contract-compliant today.

RECONCILIATION STATUS: landed on `task/m2.3` (reconciliation rewrite of
src/jarvis/kernel/memory_consolidate.py addressing FB-M2.3-1..9). The marked
probes have been flipped to assert the FIXED behavior (FB-M2.3-1, FB-M2.3-2,
FB-M2.3-3, FB-M2.3-4, FB-M2.3-5, FB-M2.3-7, FB-M2.3-8a, FB-M2.3-8b).

Targets: src/jarvis/kernel/memory_consolidate.py, src/jarvis/kernel/memory_api.py
(`Memory.consolidate`), the `memory.consolidate.superseded` audit event, and the
ratified contract text in docs/M2_3_KICKOFF.md (items A-E, subject to the M2.2
FB-M2.2-3 fold-content-stability precedent).

Findings report: docs/M2_3_REDTEAM_FB.md
"""

import pytest

from jarvis.kernel.done_gate import DoneGate, GateCheck, GateDecision
from jarvis.kernel.event_log import EventLog
from jarvis.kernel.memory_api import Memory
from jarvis.kernel.memory_consolidate import (
    MEMORY_CONSOLIDATE_REJECTED,
    MEMORY_CONSOLIDATE_SUPERSEDED,
    ConsolidationPolicy,
    MemoryConsolidator,
    _normalize,
)
from jarvis.kernel.memory_index import MemoryIndex
from jarvis.kernel.memory_trace import MemoryTraceWriter
from jarvis.kernel.memory_write import MemoryWriter

pytestmark = pytest.mark.anyio


class _FixedClock:
    def now_utc_iso(self) -> str:
        return "2026-09-18T00:00:00.000Z"


def _log(tmp_path, name: str = "fb-m2.3.db") -> EventLog:
    return EventLog(db_path=str(tmp_path / name), clock=_FixedClock())


def _trace(log: EventLog, content: str, source: str, confidence: float = 0.9) -> str:
    result = MemoryTraceWriter(log=log).record_episodic(
        content=content, source=source, confidence=confidence
    )
    assert result.status == "recorded"
    return result.event_id


def _committed(log: EventLog, content: str, source: str, confidence: float = 1.0) -> str:
    result = MemoryWriter(log=log).remember(
        content=content, source=source, confidence=confidence
    )
    assert result.status == "committed"
    return result.event_ids[-1]


def _event_types(log: EventLog) -> list[str]:
    return [event.event_type for event in log.replay()]


class _RejectingWriterGate:
    """A gate that always rejects, for the non-sticky promotion probe."""

    def evaluate(self, kind, evidence):
        return GateDecision(
            kind=kind,
            passed=False,
            checks=[GateCheck(name="confidence_valid", passed=False, detail="no")],
        )


# ---------------------------------------------------------------------------
# Group A - determinism / idempotency / crash-between-events / cap boundary
# ---------------------------------------------------------------------------


def test_a1_replay_determinism_and_zero_event_rerun(tmp_path):
    """Contract E.3: re-running consolidate() on an unchanged log emits zero
    events, and the fold digest is stable across rebuilds of the same log.

    PASS-PIN: this is the happy path the package itself claims; held."""
    log = _log(tmp_path)
    _trace(log, "The server public IP is 10.0.0.42.", "network.log")
    _trace(log, "The server public IP is 10.0.0.42.", "network.log")

    first = MemoryConsolidator(log).consolidate()
    events_after_first = _event_types(log)

    second = MemoryConsolidator(log).consolidate()

    assert len(first.promoted) == 1
    assert second.promoted == []
    assert second.skipped == {}
    assert _event_types(log) == events_after_first
    digest_1 = MemoryIndex.rebuild(log).digest()
    digest_2 = MemoryIndex.rebuild(log).digest()
    assert digest_1 == digest_2


def test_a2_audit_false_supersession_chain_bounded(tmp_path):
    """FB-M2.3-3 FIXED (FLIPPED): the already-superseded bookkeeping is now
    derived from committed provenance (the authoritative record), not from
    audit events — so `audit=False` can no longer split-brain. The weak
    original (0.5) is superseded exactly once by the first strong batch; the
    consolidation product that replaces it is excluded from same-key
    supersession (FB-M2.3-4), so later identical evidence is a confirmed
    duplicate, never churn. Gen 2/3 append nothing."""
    log = _log(tmp_path)
    _committed(log, "The server domain is alpha.", "dns", confidence=0.5)
    policy = ConsolidationPolicy(audit=False)

    for gen in range(3):
        _trace(log, "The server domain is alpha.", "dns", confidence=0.95)
        _trace(log, "The server domain is alpha.", "dns", confidence=0.95)
        result = MemoryConsolidator(log, policy=policy).consolidate()
        if gen == 0:
            assert len(result.promoted) == 1
            assert list(result.superseded.values()) == [result.promoted[0]]
        else:
            assert result.promoted == []
            assert result.superseded == {}
            # every new generation's evidence is a confirmed duplicate of the
            # product (collides); no churn, no promotion
            assert set(result.skipped.values()) == {"collides_with_committed"}

    events = _event_types(log)
    # original (0.5) + exactly ONE consolidation product across all generations
    assert events.count("memory.write.committed") == 2
    assert events.count("memory.write.proposed") == 2  # no churn: one attempt
    assert events.count(MEMORY_CONSOLIDATE_SUPERSEDED) == 0  # audit=false
    latest = list(MemoryIndex.rebuild(log).memories)[-1]
    payload = MemoryIndex.rebuild(log).memories[latest]["provenance"]
    assert payload["superseded"] is not None
    assert len(payload["superseded"]) == 1


def test_a3_third_run_does_not_supersede_own_promotion(tmp_path):
    """FB-M2.3-4 FIXED (FLIPPED): consolidation-product memories (provenance
    carries evidence_ids) are excluded from same-key supersession by default
    (`supersede_refine_gap=None`). Run 2's identical re-confirmation does not
    supersede the run-1 promotion N1 and does not promote again — a stable fact
    is promoted once. No chain, no churn."""
    log = _log(tmp_path)
    _committed(log, "The server command channel is rpc-1.", "ops", confidence=0.5)
    _trace(log, "The server command channel is rpc-1.", "ops", confidence=0.95)
    _trace(log, " The  server command channel is rpc-1.", "ops", confidence=0.95)
    run1 = MemoryConsolidator(log).consolidate()
    n1 = run1.promoted[0]

    _trace(log, "The server command channel is rpc-1.", "ops", confidence=0.97)
    _trace(log, "The server command channel is rpc-1.", "ops", confidence=0.97)
    run2 = MemoryConsolidator(log).consolidate()

    assert run2.superseded == {}
    assert run2.promoted == []
    assert list(run2.skipped.values()) == ["collides_with_committed"] * 2
    assert list(run1.superseded.values()) == [n1]  # first supersession: O -> N1


def test_a4_rejected_promotion_is_sticky_on_rerun(tmp_path):
    """FB-M2.3-5 FIXED (FLIPPED): a rejection is recorded once in a durable
    `memory.consolidate.rejected` marker (diagnostic audit event — never in the
    memories/traces folds). Later runs consume the rejected evidence_ids
    (already-consolidated iff in a marker or provenance), so re-running on an
    unchanged log appends zero events: the failed promotion cannot grow the log
    unboundedly."""
    log = _log(tmp_path)
    _trace(log, "The summit password is forty two.", "base", confidence=0.95)
    _trace(log, "The summit password is forty two.", "base", confidence=0.95)
    consolidator = MemoryConsolidator(
        log, writer=MemoryWriter(log=log, gate=_RejectingWriterGate())
    )

    run1 = consolidator.consolidate()
    after_run1 = _event_types(log)
    run2 = consolidator.consolidate()
    after_run2 = _event_types(log)

    assert list(run1.skipped.values()) == ["promotion_rejected"] * 2
    assert run2.skipped == {}
    assert after_run2 == after_run1  # FIXED: rerun appends nothing
    assert after_run2.count(MEMORY_CONSOLIDATE_REJECTED) == 1


def test_a5_max_promotions_boundary_and_order_winners(tmp_path):
    """FB-M2.3-9 (+ cap boundary pin, contract-compliant). max_promotions=1
    promotes exactly one cluster, and None promotes all — the boundary is
    correct. But the cap winners are the FIRST clusters in log order, chosen
    BEFORE confidence/gate/contradiction are evaluated: a 0.05-confidence
    cluster promoted while a 0.99-confidence cluster is capped. Deterministic,
    but the winner set is decided by insertion order, not by any policy datum."""
    log_capped = _log(tmp_path, "capped.db")
    _trace(log_capped, "The scratch paper color is beige.", "lab", confidence=0.05)
    _trace(log_capped, "The scratch paper color is beige.", "lab", confidence=0.05)
    _trace(log_capped, "The launch window closes at noon sharp.", "ops", confidence=0.99)
    _trace(log_capped, "The launch window closes at noon sharp.", "ops", confidence=0.99)

    capped = MemoryConsolidator(
        log_capped, policy=ConsolidationPolicy(promote={"max_promotions": 1})
    ).consolidate()

    log_free = _log(tmp_path, "free.db")
    _trace(log_free, "The scratch paper color is beige.", "lab", confidence=0.05)
    _trace(log_free, "The scratch paper color is beige.", "lab", confidence=0.05)
    _trace(log_free, "The launch window closes at noon sharp.", "ops", confidence=0.99)
    _trace(log_free, "The launch window closes at noon sharp.", "ops", confidence=0.99)
    unlimited = MemoryConsolidator(log_free).consolidate()

    assert len(capped.promoted) == 1  # boundary pin (PASS)
    assert len(unlimited.promoted) == 2  # boundary pin (PASS)
    content = MemoryIndex.rebuild(log_capped).memories[capped.promoted[0]]["content"]
    assert "scratch paper" in content  # the WEAK earliest cluster won the cap (LOW)


# ---------------------------------------------------------------------------
# Group B - decisioning is DATA (not-branches) fidelity
# ---------------------------------------------------------------------------


def test_b1_any_key_same_source_gate_decides_by_source(tmp_path):
    """FB-M2.3-2 FIXED (FLIPPED): the decision table now expresses all three
    declared gates. `any_key_same_source` constructs and evaluates: a candidate
    matching a committed memory on source supersedes it REGARDLESS of content
    key (whereas `same_key_same_source` would not match different content)."""
    policy = ConsolidationPolicy(contradiction={"gate": "any_key_same_source"})
    assert policy.contradiction.gate == "any_key_same_source"

    log = _log(tmp_path)
    _committed(log, "The server domain is alpha.", "dns", confidence=0.5)
    _trace(log, "The BGP peer is 192.0.2.1.", "dns", confidence=0.95)
    _trace(log, "The BGP peer is 192.0.2.1.", "dns", confidence=0.95)
    result = MemoryConsolidator(log, policy=policy).consolidate()

    assert len(result.promoted) == 1
    assert len(result.superseded) == 1  # same source, any key -> superseded


def test_b2_normalize_modes_are_distinct(tmp_path):
    """FB-M2.3-7 FIXED (FLIPPED): the three declared modes are strictly
    distinct: exact = strip only (whitespace AND case preserved), lower = strip
    + casefold (whitespace preserved), fold = strip + whitespace-collapse +
    casefold."""
    assert _normalize("A  B", "exact") != _normalize("A B", "exact")  # whitespace kept
    assert _normalize("Ab C", "exact") != _normalize("ab c", "exact")  # case kept
    assert _normalize("A  B", "lower") != _normalize("A B", "fold")  # collapse differs
    assert _normalize("Ab C", "lower") == _normalize("ab c", "lower")
    assert _normalize(" A  B ", "fold") == _normalize("A B", "fold")


# ---------------------------------------------------------------------------
# Group C - consume/dedupe correctness and provenance shape abuse
# ---------------------------------------------------------------------------


def test_c1_string_evidence_ids_is_one_reference(tmp_path):
    """FB-M2.3-8a FIXED (FLIPPED): a STRING `evidence_ids` is ONE reference
    (never scanned character-by-character). The trace id the malformed memory
    references is consumed, so it cannot be promoted a second time: no
    duplication, and the remaining lone trace falls below evidence_min."""
    log = _log(tmp_path)
    t1 = _trace(log, "The repository root is src.", "ci", confidence=0.95)
    t2 = _trace(log, "The repository root is src.", "ci", confidence=0.95)
    _committed_malformed = MemoryWriter(log=log).remember(
        content="The repository root is src.",
        source="ci",
        confidence=0.6,
        provenance={"evidence_ids": t1, "superseded": None},
    )
    assert _committed_malformed.status == "committed"

    result = MemoryConsolidator(log).consolidate()

    assert result.promoted == []  # FIXED: t1 was referenced, must be consumed
    assert list(result.skipped.values()) == ["below_evidence_min"]


def test_c2_int_evidence_ids_never_crashes_consolidate(tmp_path):
    """FB-M2.3-8b FIXED (FLIPPED): a non-list, non-string `evidence_ids` is a
    shape violation handled WITHOUT crashing — no references are consumed from
    it, the consume scan continues, and consolidation proceeds normally (the
    malformed memory is treated as an original and superseded by the strong,
    real evidence cluster)."""
    log = _log(tmp_path)
    _trace(log, "The repository root is src.", "ci", confidence=0.95)
    _trace(log, "The repository root is src.", "ci", confidence=0.95)
    malformed = MemoryWriter(log=log).remember(
        content="The repository root is src.",
        source="ci",
        confidence=0.6,
        provenance={"evidence_ids": 42},
    )
    malformed_id = malformed.event_ids[-1]

    result = MemoryConsolidator(log).consolidate()  # FIXED: types itself, never raws

    assert len(result.promoted) == 1
    assert list(result.superseded.keys()) == [malformed_id]


def test_c3_evidence_min_and_confidence_floor_boundaries(tmp_path):
    """Boundary pins (contract-compliant PASS): evidence_min=1 promotes a
    lone trace; a cluster whose min confidence equals confidence_floor
    promotes (>=); and the promoted-with-1-evidence log then reruns with zero
    events."""
    log = _log(tmp_path)
    t1 = _trace(log, "The rendezvous is at the north gate.", "agent", confidence=0.5)
    policy = ConsolidationPolicy(
        extract={"evidence_min": 1}, promote={"confidence_floor": 0.5}
    )

    run1 = MemoryConsolidator(log, policy=policy).consolidate()
    assert len(run1.promoted) == 1
    assert run1.skipped == {}
    assert t1 in MemoryIndex.rebuild(log).memories[run1.promoted[0]]["provenance"]["evidence_ids"]

    baseline = _event_types(log)
    run2 = MemoryConsolidator(log, policy=policy).consolidate()
    assert run2.promoted == []
    assert _event_types(log) == baseline


# ---------------------------------------------------------------------------
# Group D - fold/digest stability (FB-M2.2-3 precedent applied to M2.3)
# ---------------------------------------------------------------------------


def test_d1_superseded_event_folds_stable_but_digest_moves(tmp_path):
    """FB-M2.3-6. R2 holds: the memory.consolidate.superseded event never
    enters the memories/traces folds. But it lives on stream "memory", so it
    IS counted by MemoryIndex.event_count and streams["memory"], and
    MemoryIndex.digest() hashes the whole projection state — so the ratified
    E.4 wording "MemoryIndex digest unchanged by the supersede event" is not
    what the shipped fold delivers. This mirrors the FB-M2.2-3 ruling
    (accepted contract-rewording 'digest inputs -> fold inputs'); the probes
    below PIN the fold-content stability (good) and the digest movement
    (documented, for the ruling)."""
    log = _log(tmp_path)
    _committed(log, "The server command channel is rpc-1.", "ops", confidence=0.5)
    t1 = _trace(log, "The server command channel is rpc-1.", "ops", confidence=0.95)
    t2 = _trace(log, "The server command channel is rpc-1.", "ops", confidence=0.95)

    pre = MemoryIndex.rebuild(log)
    MemoryConsolidator(log).consolidate()
    post = MemoryIndex.rebuild(log)
    supersede_events = [
        e for e in log.replay() if e.event_type == MEMORY_CONSOLIDATE_SUPERSEDED
    ]

    assert len(post.memories) == 2
    assert set(post.traces) == {t1, t2}
    assert len(supersede_events) == 1
    assert post.event_count == pre.event_count + 4  # 3 write + 1 superseded
    assert post.streams["memory"] == supersede_events[-1].stream_seq
    assert MemoryIndex.rebuild(log).digest() == MemoryIndex.rebuild(log).digest()


# ---------------------------------------------------------------------------
# Group E - promotion path: principal stamping and content source
# ---------------------------------------------------------------------------


def test_e1_principal_stamp_one_principal_for_consolidation(tmp_path):
    """FB-M2.3-1 FIXED (FLIPPED): MemoryConsolidator(log, principal_id="drone")
    stamps the promotion chain (proposed/verified/committed) AND the
    memory.consolidate.superseded audit event "drone" — one consolidation, one
    principal. The constructor principal is the caller-declared authoring
    principal (kickoff B, FB-M2.2-7 precedent); the audit no longer silently
    re-authors it as the policy default."""
    log = _log(tmp_path)
    _committed(log, "The server command channel is rpc-1.", "ops", confidence=0.5)
    _trace(log, "The server command channel is rpc-1.", "ops", confidence=0.95)
    _trace(log, "The server command channel is rpc-1.", "ops", confidence=0.95)

    MemoryConsolidator(log, principal_id="drone").consolidate()

    drone_writes = [
        e
        for e in log.replay()
        if e.event_type.startswith("memory.write.") and e.principal_id == "drone"
    ]
    audit_principals = {
        e.principal_id
        for e in log.replay()
        if e.event_type == MEMORY_CONSOLIDATE_SUPERSEDED
    }
    assert len(drone_writes) == 3  # the drone-declared promotion chain
    assert len(audit_principals) == 1
    # FIXED (FB-M2.3-1): one consolidation, one principal — the constructor
    # principal stamps the audit event as well, not the policy default.
    assert audit_principals == {"drone"}


def test_e2_facade_consolidate_principal_stamp(tmp_path):
    """FB-M2.3-1 via the facade: Memory(log=log).consolidate(principal_id=...)
    forwards the declared principal to the consolidator; the audit event is
    stamped with it (no split with the policy default)."""
    log = _log(tmp_path)
    _committed(log, "The server command channel is rpc-1.", "ops", confidence=0.5)
    _trace(log, "The server command channel is rpc-1.", "ops", confidence=0.95)
    _trace(log, "The server command channel is rpc-1.", "ops", confidence=0.95)

    Memory(log=log).consolidate(principal_id="drone")

    audit = [
        e for e in log.replay() if e.event_type == MEMORY_CONSOLIDATE_SUPERSEDED
    ]
    assert len(audit) == 1
    # FIXED (FB-M2.3-1): facade forwards the caller principal to the
    # consolidator, which stamps the audit event with it, not "creator".
    assert audit[0].principal_id == "drone"


def test_e3_committed_content_is_last_trace_in_log_order(tmp_path):
    """INFO pin (documented behavior, no flip recommended): the promoted
    memory's raw content is members[-1] — the LAST trace of the cluster in log
    order — not any policy datum. Two traces whose normalized keys match but
    whose raw text differs produce a committed memory carrying the last
    appended raw variant."""
    log = _log(tmp_path)
    t1 = _trace(log, "The  server command channel is rpc-1.", "ops", confidence=0.95)
    t2 = _trace(log, "The server command channel is rpc-1.", "ops", confidence=0.98)

    result = MemoryConsolidator(log).consolidate()
    payload = MemoryIndex.rebuild(log).memories[result.promoted[0]]

    assert payload["content"] == "The server command channel is rpc-1."
    assert payload["provenance"]["evidence_ids"] == [t1, t2]