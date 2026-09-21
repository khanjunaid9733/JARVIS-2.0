from __future__ import annotations

"""M2.5 - the FROZEN_SUCCESS ratchet seal and the creator-gated REOPEN edge.

Once a task reaches PASS and is sealed, it enters FROZEN_SUCCESS: a TERMINAL,
ABSORBING state. A worker cannot edit, re-test, or reopen it; the ONLY outgoing
edge is creator-gated REOPEN (84.4 ladder). Any post-seal byte drift is a
MUTATION report (mutation_guard), never a weak edit. Hermetic: no model calls,
no ambient clocks, no ambient reads.

Bindings note: Sentinel datums are authoritative - a Supervisor bound to a
FROZEN_SUCCESS ratchet (TaskLifecycle) answers an absorbing decision for every
worker-reachable event, exactly the hard stop the M2.4 drift demanded.
"""

import pytest

from jarvis.supervisor import (
    EvidenceLedger,
    EvidenceSource,
    LifecycleEvent,
    LifecycleState,
    MutationGuard,
    PackageSnapshot,
    Supervisor,
    TaskLifecycle,
    VerificationResult,
)

ISO = "2026-09-21T00:00:00.000Z"


def _frozen_supervisor() -> Supervisor:
    return Supervisor(
        lifecycle=TaskLifecycle(state=LifecycleState.FROZEN_SUCCESS),
        ledger=EvidenceLedger(observed_at=ISO),
    )


def test_frozen_success_is_terminal_and_absorbing() -> None:
    """FROZEN_SUCCESS absorbs every worker-reachable event in the table."""
    lc = TaskLifecycle(state=LifecycleState.PASS)
    lc = lc.apply(LifecycleEvent.FREEZE)
    assert lc.frozen_success is True
    assert lc.state is LifecycleState.FROZEN_SUCCESS

    for event in LifecycleEvent:
        if event is LifecycleEvent.REOPEN:
            # REOPEN is THE only edge; it is creator-gated and non-creator apply
            # must leave the ratchet sealed (apply() refuses creator edges).
            continue
        assert lc.apply(event).state is LifecycleState.FROZEN_SUCCESS


def test_only_creator_gated_reopen_moves_frozen_success() -> None:
    """A worker asking for REOPEN is told REJECTED; the creator is not."""
    lc = TaskLifecycle(state=LifecycleState.PASS)
    lc = lc.apply(LifecycleEvent.FREEZE)

    worker = lc.declared_transition(LifecycleEvent.REOPEN, as_creator=False)
    assert worker.rejected is True
    assert worker.transition is not None
    assert worker.transition.creator_gated is True
    assert worker.next_state is None

    creator = lc.declared_transition(LifecycleEvent.REOPEN, as_creator=True)
    assert creator.rejected is False
    assert creator.next_state is LifecycleState.IMPLEMENTING


def test_supervisor_freeze_returns_frozen_success_datum() -> None:
    """Supervisor.freeze returns the FROZEN_SUCCESS decision datum with a
    creator-gated marker, and moves the bound ratchet to FROZEN_SUCCESS."""
    snap = PackageSnapshot(blob_hashes={"a.py": "hash-1"}, sealed_at=ISO)
    sup = Supervisor(
        lifecycle=TaskLifecycle(state=LifecycleState.PASS),
        ledger=EvidenceLedger(observed_at=ISO),
    )
    decision = sup.freeze(observed_at=ISO, snapshot=snap)

    assert decision.verdict == "FROZEN_SUCCESS"
    assert decision.frozen_success is True
    assert decision.creator_gated is True
    assert decision.reason == "ratchet sealed: FROZEN_SUCCESS"
    assert sup.frozen_success is True


def test_once_frozen_no_worker_claim_moves_the_datum() -> None:
    """After freeze, Supervisor.decide returns the ABSORBING FROZEN_SUCCESS
    decision with a creator-gated marker - never a transition back to work."""
    sup = _frozen_supervisor()
    decision = sup.decide(worker_claim=True, observed_at=ISO)
    assert decision.verdict == "FROZEN_SUCCESS"
    assert decision.frozen_success is True
    assert decision.creator_gated is True
    assert decision.state is LifecycleState.FROZEN_SUCCESS
    verifier_datum = decision.verifier
    assert isinstance(verifier_datum, VerificationResult)
    assert verifier_datum.source is EvidenceSource.IMMUTABLE_ARTIFACT
    assert verifier_datum.value is True


def test_post_freeze_byte_drift_is_a_report_not_an_edit() -> None:
    """A mutated current snapshot produces mutated=True with the changed path,
    exactly the class of drift that must surface as a MUTATION (t18)."""
    seal = {"src/a.py": "ABBA", "src/b.py": "BEEF"}
    snap = PackageSnapshot(blob_hashes=seal, sealed_at=ISO)
    guard = MutationGuard()
    guard.seal(snap)

    drifted = PackageSnapshot(
        blob_hashes={"src/a.py": "MOO!", "src/b.py": "BEEF"}, sealed_at=ISO
    )
    report = guard.check(current=drifted)
    assert report.mutated is True
    assert "src/a.py" in report.changed
    assert report.removed == ()
    assert report.added == ()


def test_guard_cannot_be_resealed_by_a_worker() -> None:
    """One seal per guard lifetime; a second seal raises (ratchet: a worker
    cannot un-seal frozen bytes)."""
    guard = MutationGuard()
    guard.seal(PackageSnapshot(blob_hashes={"a": "h1"}, sealed_at=ISO))
    with pytest.raises(ValueError):
        guard.seal(PackageSnapshot(blob_hashes={"a": "h2"}, sealed_at=ISO))