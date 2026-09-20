from __future__ import annotations

"""T18 - the M2.4 context-drift ratchet (M2.5, spec 84.4).

The M2.4 failure: a worker claimed PASS, kept editing post-PASS, the edit
broke the package (fresh pytest -> SyntaxError during collection), and the
worker argued AGAINST the fresh machine datum using stale memory. T18 seals
the rule that a fresh FILESYSTEM datum outranks AGENT_MEMORY, that a
post-PASS edit is detected as a mutation, and that recovery is a fold of the
ledger. Hermetic: no model calls, no ambient clocks, no ambient reads.
"""

import pytest

from jarvis.supervisor.authority import (
    AuthorityTier,
    EscalationReason,
    decide_authority_tier,
    is_creator_gated,
)
from jarvis.supervisor.evidence import (
    Evidence,
    EvidenceLedger,
    EvidencePrecedence,
    EvidenceSource,
)
from jarvis.supervisor.lifecycle import (
    LifecycleEvent,
    LifecycleState,
    TaskLifecycle,
)
from jarvis.supervisor.mutation_guard import (
    MutationGuard,
    MutationReport,
    PackageSnapshot,
)
from jarvis.supervisor.recovery import (
    RecoveryAction,
    RecoveryPlan,
    RecoveryPolicy,
    decide_recovery,
)
from jarvis.supervisor.supervisor import (
    Supervisor,
    SupervisorDecision,
    Verifier,
)

pytestmark = pytest.mark.anyio

ISO = "2026-09-19T00:00:00.000Z"


def test_t18_fresh_filesystem_datum_outranks_stale_worker_memory() -> None:
    """The ledger holds a fresh FILESYSTEM datum. An AGENT_MEMORY datum that
    claimed PASS moments ago is outranked. The authority is FILESYSTEM.
    """
    ledger = EvidenceLedger(
        observed_at=ISO,
        entries=(
            Evidence(
                source=EvidenceSource.FILESYSTEM,
                precedence=EvidencePrecedence.FILESYSTEM,
                summary="uv pytest: 'SyntaxError during collection (exit 2)'",
                observed_at=ISO,
            ),
            Evidence(
                source=EvidenceSource.AGENT_MEMORY,
                precedence=EvidencePrecedence.AGENT_MEMORY,
                summary="stale claim: 'my tests passed a moment ago'",
                observed_at=ISO,
            ),
        ),
    )
    authority = ledger.authority()
    assert authority is not None
    assert authority.source is EvidenceSource.FILESYSTEM
    assert authority.precedence == EvidencePrecedence.FILESYSTEM

    # Conflicts check: lower precedence claim conflicts with higher authority
    stale_claim = Evidence(
        source=EvidenceSource.AGENT_MEMORY,
        precedence=EvidencePrecedence.AGENT_MEMORY,
        summary="stale claim",
        observed_at=ISO,
    )
    conflict = ledger.conflicts(stale_claim)
    assert conflict is not None
    assert conflict.source is EvidenceSource.FILESYSTEM


def test_t18_mutation_guard_reports_mutated_after_pass() -> None:
    """MutationGuard sealed at PASS detects post-PASS byte mutation."""
    sealed = PackageSnapshot(
        blob_hashes={"tests/supervisor/test_t18_context_drift.py": "seal-1"},
        sealed_at=ISO,
    )
    guard = MutationGuard()
    guard.seal(sealed)
    assert guard.sealed is True

    # Same snapshot -> not mutated
    report_clean = guard.check(current=sealed)
    assert report_clean.mutated is False

    # Mutated snapshot -> mutated is True
    current = PackageSnapshot(
        blob_hashes={"tests/supervisor/test_t18_context_drift.py": "MUTATED"},
        sealed_at=ISO,
    )
    report = guard.check(current=current)
    assert isinstance(report, MutationReport)
    assert report.mutated is True
    assert "tests/supervisor/test_t18_context_drift.py" in report.changed


def test_t18_recovery_is_a_fold_of_the_ledger_not_worker_narration() -> None:
    """decide_recovery over the SAME ledger + SAME state + SAME attempts ->
    the SAME plan every time (deterministic fold).
    """
    ledger = EvidenceLedger(
        observed_at=ISO,
        entries=(
            Evidence(
                source=EvidenceSource.FILESYSTEM,
                precedence=EvidencePrecedence.FILESYSTEM,
                summary="fresh: SyntaxError during collection (precedent exit-2)",
                observed_at=ISO,
            ),
            Evidence(
                source=EvidenceSource.AGENT_MEMORY,
                precedence=EvidencePrecedence.AGENT_MEMORY,
                summary="worker: 'my tests passed' (stale; post-PASS edit broke the package)",
                observed_at=ISO,
            ),
        ),
    )

    # In FAILED state with fresh evidence and attempts < max, action is RETRY
    plan_a = decide_recovery(
        state=LifecycleState.FAILED,
        ledger=ledger,
        attempts_used=2,
        policy=RecoveryPolicy(max_attempts=3, rollback_available=True),
        reason="post-PASS mutation datum outranks worker PASS claim",
    )
    plan_b = decide_recovery(
        state=LifecycleState.FAILED,
        ledger=ledger,
        attempts_used=2,
        policy=RecoveryPolicy(max_attempts=3, rollback_available=True),
        reason="post-PASS mutation datum outranks worker PASS claim",
    )
    assert plan_a.action is plan_b.action
    assert plan_a.action is RecoveryAction.RETRY

    # When attempts exhausted and rollback available, action is ROLLBACK
    plan_exhausted = decide_recovery(
        state=LifecycleState.FAILED,
        ledger=ledger,
        attempts_used=3,
        policy=RecoveryPolicy(max_attempts=3, rollback_available=True),
        reason="recovery attempts exhausted",
    )
    assert plan_exhausted.action is RecoveryAction.ROLLBACK


def test_t18_frozen_success_is_absorbing_to_worker() -> None:
    """FROZEN_SUCCESS is terminal for workers. Only creator-gated REOPEN moves it."""
    lc = TaskLifecycle(state=LifecycleState.PASS)
    lc = lc.apply(LifecycleEvent.FREEZE)
    assert lc.state is LifecycleState.FROZEN_SUCCESS
    assert lc.frozen_success is True

    # Worker edit_start is absorbed (state unchanged)
    lc_worker = lc.apply(LifecycleEvent.EDIT_START)
    assert lc_worker.state is LifecycleState.FROZEN_SUCCESS

    # Worker reopen is rejected
    decision_worker = lc.declared_transition(LifecycleEvent.REOPEN, as_creator=False)
    assert decision_worker.rejected is True
    assert decision_worker.transition is not None
    assert decision_worker.transition.creator_gated is True

    # Creator reopen succeeds and moves to IMPLEMENTING
    decision_creator = lc.declared_transition(LifecycleEvent.REOPEN, as_creator=True)
    assert decision_creator.rejected is False
    assert decision_creator.next_state is LifecycleState.IMPLEMENTING


def test_t18_authority_ladder_is_data() -> None:
    """Authority tiers are declared data. Only L2 reasons are creator-gated."""
    assert decide_authority_tier(EscalationReason.MERGE_PUSH) is AuthorityTier.L2
    assert is_creator_gated(EscalationReason.MERGE_PUSH) is True

    assert decide_authority_tier(EscalationReason.CONTEXT_DRIFT) is AuthorityTier.L1
    assert is_creator_gated(EscalationReason.CONTEXT_DRIFT) is False

    assert decide_authority_tier(EscalationReason.STALLED) is AuthorityTier.L0
    assert is_creator_gated(EscalationReason.STALLED) is False
