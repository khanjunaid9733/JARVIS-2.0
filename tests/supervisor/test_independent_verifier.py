from __future__ import annotations

"""M2.5 - the INDEPENDENT verifier seam (I2, FROZEN acceptance law).

A worker claims success; an INDEPENDENT verifier - and only it - produces the
datum that moves the ratchet to PASS. The verifier is never the worker: it is
a separate seam that re-runs the acceptance surface and returns a FRESH
VerificationResult with executable authority (FRESH_VERIFIER). A workers'
narration can never set a true value. Hermetic: the verifier below is an
injected stub; nothing here calls pytest, reads the FS, or reads a clock.

Binding notes: the Supervisor DELIVERS decision datums; the ratchet state is a
property of the bound TaskLifecycle. PASS verdict == a claim label
(`decide`), rendered honest by `verifier.value is False`; PASS state ==
following independent verification. Freeze seals ONLY from PASS.
"""

from jarvis.supervisor import (
    EvidenceLedger,
    EvidencePrecedence,
    EvidenceSource,
    LifecycleState,
    PackageSnapshot,
    Supervisor,
    SupervisorDecision,
    TaskLifecycle,
    VerificationResult,
    Verifier,
)

ISO = "2026-09-21T00:00:00.000Z"


class _PassingVerifier(Verifier):
    """Fresh independent datum: the acceptance surface passed."""

    def verify(self) -> VerificationResult:
        return VerificationResult.decided(
            value=True,
            source=EvidenceSource.FRESH_VERIFIER,
            observed_at=ISO,
            summary="independent re-run: 486 passed, 0 failed",
        )


class _FailingVerifier(Verifier):
    """Fresh independent datum: the acceptance surface fails."""

    def verify(self) -> VerificationResult:
        return VerificationResult.decided(
            value=False,
            source=EvidenceSource.FRESH_VERIFIER,
            observed_at=ISO,
            summary="independent re-run: exit 2, collection error",
        )


class _NarrationImpostor(Verifier):
    """A worker-sized verifier that RETURNS a datum instead of measuring one:
    value from AGENT_MEMORY - this must NEVER flip the ratchet."""

    def verify(self) -> VerificationResult:
        return VerificationResult.decided(
            value=True,  # a claimed PASS
            source=EvidenceSource.AGENT_MEMORY,  # ...but only narration, no bytes
            observed_at=ISO,
            summary="worker: trust me, it passes",
        )


def _implementing_supervisor() -> Supervisor:
    return Supervisor(
        lifecycle=TaskLifecycle(state=LifecycleState.IMPLEMENTING),
        ledger=EvidenceLedger(observed_at=ISO),
    )


def test_worker_claim_alone_never_reaches_pass() -> None:
    """I2: a worker's claim enters at AGENT_MEMORY and stops at WORKER_VERIFY.
    PASS requires the independent datum - the claim must be explicitly tagged
    value=False so nothing below can mistake it for a verdict."""
    sup = _implementing_supervisor()
    decision = sup.decide(worker_claim=True, observed_at=ISO)
    assert isinstance(decision, SupervisorDecision)
    assert decision.state is LifecycleState.WORKER_VERIFY
    assert decision.verdict == "PASS"  # the CLAIM label - not acceptance
    assert decision.verifier.value is False  # clearly marked: not a verdict
    assert decision.verifier.source is EvidenceSource.AGENT_MEMORY


def test_successful_independent_verification_moves_to_pass() -> None:
    """Only a FRESH verifier datum (value=True) advances the ratchet to PASS."""
    sup = _implementing_supervisor()
    decision = sup.verify(verifier=_PassingVerifier(), observed_at=ISO)
    assert decision.state is LifecycleState.PASS
    assert decision.verdict == "PASS"
    assert decision.passed is True
    assert decision.verifier.value is True
    assert decision.verifier.source is EvidenceSource.FRESH_VERIFIER


def test_failed_independent_verification_goes_to_failed() -> None:
    sup = _implementing_supervisor()
    decision = sup.verify(verifier=_FailingVerifier(), observed_at=ISO)
    assert decision.state is LifecycleState.FAILED
    assert decision.verdict == "FAIL"
    assert decision.passed is False
    assert decision.verifier.value is False


def test_narration_without_bytes_cannot_move_the_ratchet() -> None:
    """A verifier returning a datum sourced from AGENT_MEMORY flips NOTHING:
    PASS requires FRESH_VERIFIER/executable authority, never a claim."""
    sup = _implementing_supervisor()
    decision = sup.verify(verifier=_NarrationImpostor(), observed_at=ISO)
    assert decision.state is LifecycleState.FAILED
    assert decision.verdict == "FAIL"
    assert decision.passed is False


def test_pass_is_frozen_only_by_freeze() -> None:
    """PASS is a rung, not a seal: FROZEN_SUCCESS arrives only from the
    mutation guard's freeze once the ratchet sits AT PASS."""
    sup = Supervisor(
        lifecycle=TaskLifecycle(state=LifecycleState.PASS),
        ledger=EvidenceLedger(observed_at=ISO),
    )
    decision = sup.verify(verifier=_PassingVerifier(), observed_at=ISO)
    assert decision.state is LifecycleState.PASS

    frozen = sup.freeze(
        observed_at=ISO, snapshot=PackageSnapshot(blob_hashes={}, sealed_at=ISO)
    )
    assert frozen.state is LifecycleState.FROZEN_SUCCESS
    assert frozen.verdict == "FROZEN_SUCCESS"
    assert frozen.passed is True
    assert sup.frozen_success is True


def test_ratchet_never_releases_a_frozen_datum_on_worker_claim() -> None:
    """Even with a fresh passing verifier, a FROZEN_SUCCESS ratchet is
    absorbing: the only edge is creator-gated REOPEN, and the worker is not
    the creator."""
    sup = Supervisor(
        lifecycle=TaskLifecycle(state=LifecycleState.FROZEN_SUCCESS),
        ledger=EvidenceLedger(observed_at=ISO),
    )
    decision = sup.decide(worker_claim=True, observed_at=ISO)
    assert decision.verdict == "FROZEN_SUCCESS"
    assert decision.creator_gated is True


def test_verifier_evidence_is_appended_to_the_ledger() -> None:
    """verify() appends the fresh datum's Evidence to the ledger (append-only
    fold), so the decision trace is reconstructible."""
    sup = _implementing_supervisor()
    decision = sup.verify(verifier=_PassingVerifier(), observed_at=ISO)
    ledger: EvidenceLedger = decision.ledger
    assert ledger.highest().source is EvidenceSource.FRESH_VERIFIER
    assert ledger.highest().precedence is EvidencePrecedence.FRESH_VERIFIER
    assert ledger.highest() is not None