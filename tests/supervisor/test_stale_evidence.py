from __future__ import annotations

"""M2.5 - evidence staleness, precedence, and conflict resolution (84.4).

The evidence hierarchy is DATA: lower ordinal source = higher authority, and a
claim can never outrank what the source can support. A stale datum (old
observation about a changed world) carries no authority until re-taken;
the FROZEN_SUCCESS drift failure of M2.4 is exactly the class this seals.
Hermetic: no model calls, no ambient clocks, no ambient reads.
"""

from jarvis.supervisor import (
    Evidence,
    EvidenceLedger,
    EvidencePrecedence,
    EvidenceSource,
    VerificationResult,
)

ISO = "2026-09-21T00:00:00.000Z"
EARLIER = "2026-09-20T00:00:00.000Z"


def test_precedence_rungs_are_exactly_the_declared_hierarchy() -> None:
    """Lower ordinal = higher authority; FILESYSTEM is the top rung."""
    assert EvidenceSource.FILESYSTEM.value == "filesystem"
    assert EvidencePrecedence.FILESYSTEM == 7
    assert EvidencePrecedence.AGENT_MEMORY == 1
    ordered = sorted(EvidencePrecedence, key=lambda p: p.value, reverse=True)
    assert ordered[0] is EvidencePrecedence.FILESYSTEM
    assert ordered[-1] is EvidencePrecedence.AGENT_MEMORY


def test_declare_binds_source_to_its_declared_precedence() -> None:
    """Evidence.declare must attach the source's OWN precedence (data, never
    derived from narration)."""
    fresh = Evidence.declare(
        source=EvidenceSource.FILESYSTEM,
        summary="uv pytest exit 0",
        observed_at=ISO,
    )
    assert fresh.precedence is EvidencePrecedence.FILESYSTEM
    assert fresh.datum == ""

    memory = Evidence.declare(
        source=EvidenceSource.AGENT_MEMORY,
        summary="worker claims green",
        observed_at=ISO,
    )
    assert memory.precedence is EvidencePrecedence.AGENT_MEMORY


def test_fresh_filesystem_outranks_recent_stale_memory() -> None:
    """Freshness is a gate: a FILESYSTEM datum just taken outranks a memory
    claim even when the claim is timestamped NEWER (M2.4 drift class)."""
    ledger = EvidenceLedger(
        observed_at=ISO,
        entries=(
            Evidence.declare(
                source=EvidenceSource.AGENT_MEMORY,
                summary="stale claim: 'passed a moment ago'",
                observed_at=ISO,  # narratively recent
            ),
            Evidence.declare(
                source=EvidenceSource.FILESYSTEM,
                summary="fresh re-run: 486 passed",
                observed_at=ISO,
            ),
        ),
    )
    authority = ledger.authority()
    assert authority is not None
    assert authority.source is EvidenceSource.FILESYSTEM
    assert ledger.highest() is authority


def test_old_filesystem_datum_outranks_memory_too() -> None:
    """Within the hierarchy, source wins regardless of order of entry; the
    ledger folds entries, it never reorders them by clock."""
    ledger = EvidenceLedger(
        observed_at=EARLIER,
        entries=(
            Evidence.declare(
                source=EvidenceSource.FILESYSTEM,
                summary="older but byte datum",
                observed_at=EARLIER,
            ),
            Evidence.declare(
                source=EvidenceSource.AGENT_MEMORY,
                summary="newer memory",
                observed_at=ISO,
            ),
        ),
    )
    assert ledger.authority().source is EvidenceSource.FILESYSTEM


def test_conflicts_return_authoritative_datum_only_when_overruled() -> None:
    """conflicts() returns the higher datum only when the claim is LOWER
    precedence; equal/empty ledger yields None."""
    ledger = EvidenceLedger(
        observed_at=ISO,
        entries=(
            Evidence.declare(
                source=EvidenceSource.FILESYSTEM,
                summary="fresh: syntax error (exit 2)",
                observed_at=ISO,
            ),
        ),
    )
    stale_claim = Evidence.declare(
        source=EvidenceSource.AGENT_MEMORY,
        summary="claim: all green",
        observed_at=ISO,
    )
    conflict = ledger.conflicts(stale_claim)
    assert conflict is not None
    assert conflict.source is EvidenceSource.FILESYSTEM


def test_equal_precedence_claim_does_not_conflict() -> None:
    ledger = EvidenceLedger(
        observed_at=ISO,
        entries=(
            Evidence.declare(
                source=EvidenceSource.TOOL_OUTPUT,
                summary="tool text A",
                observed_at=ISO,
            ),
        ),
    )
    claim = Evidence.declare(
        source=EvidenceSource.TOOL_OUTPUT,
        summary="tool text B",
        observed_at=ISO,
    )
    assert ledger.conflicts(claim) is None


def test_empty_ledger_has_no_authority() -> None:
    ledger = EvidenceLedger(observed_at=ISO)
    assert ledger.authority() is None
    assert ledger.highest() is None


def test_ledger_is_immutable_and_additive_fold() -> None:
    """with_entry must never mutate the prior ledger (fold precedent)."""
    original = EvidenceLedger(observed_at=ISO)
    added = original.with_entry(
        Evidence.declare(source=EvidenceSource.FILESYSTEM, summary="x", observed_at=ISO)
    )
    assert len(original.entries) == 0
    assert len(added.entries) == 1


def test_verification_result_decision_carries_its_evidence_datum() -> None:
    """VerificationResult.decided attaches a fresh Evidence datum so the result
    is a fold of the ledger, never a bare bool."""
    fresh_true = VerificationResult.decided(
        value=True,
        source=EvidenceSource.FRESH_VERIFIER,
        observed_at=ISO,
        summary="independent verifier: PASS",
    )
    assert fresh_true.value is True
    assert fresh_true.source is EvidenceSource.FRESH_VERIFIER
    assert fresh_true.evidence.source is EvidenceSource.FRESH_VERIFIER
    assert fresh_true.evidence.summary == "independent verifier: PASS"