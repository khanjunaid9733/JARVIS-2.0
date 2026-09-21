from __future__ import annotations

"""M2.5 - recovery ladder: bounded repair is a fold of the ledger (84.4).

`decide_recovery` is PURE DATA: same state + same ledger + same attempts + same
policy -> the SAME action, always. The worker never "decides what to do next" -
it consults the RecoveryPolicy ladder datum: RETRY / RESTART / ROLLBACK /
ESCALATE / HOLD / NONE. Recovery performs NO effects and makes NO model calls
(formal hermetic law, kickoff E / F-C9). Hermetic: no I/O in this file.
"""

import pytest

from jarvis.supervisor import (
    Evidence,
    EvidenceLedger,
    EvidenceSource,
    LifecycleState,
    RecoveryAction,
    RecoveryPlan,
    RecoveryPolicy,
    decide_recovery,
)

ISO = "2026-09-21T00:00:00.000Z"


def _fresh_ledger() -> EvidenceLedger:
    return EvidenceLedger(
        observed_at=ISO,
        entries=(
            Evidence.declare(
                source=EvidenceSource.FILESYSTEM,
                summary="fresh: pytest exit 2 (SyntaxError during collection)",
                observed_at=ISO,
            ),
        ),
    )


def test_recovery_has_exactly_six_declared_actions() -> None:
    assert [a for a in RecoveryAction] == list(RecoveryAction)
    assert RecoveryAction.NONE.value == "none"
    assert RecoveryAction.RETRY.value == "retry"
    assert RecoveryAction.RESTART.value == "restart"
    assert RecoveryAction.ROLLBACK.value == "rollback"
    assert RecoveryAction.ESCALATE.value == "escalate"
    assert RecoveryAction.HOLD.value == "hold"


def test_none_when_state_is_not_a_failure() -> None:
    """Outside FAILED/HELD the ladder declares NONE - nothing to do."""
    for state in (LifecycleState.PROPOSED, LifecycleState.IMPLEMENTING, LifecycleState.WORKER_VERIFY, LifecycleState.PASS, LifecycleState.FROZEN_SUCCESS, LifecycleState.REPAIRING, LifecycleState.ESCALATED):
        plan = decide_recovery(
            state=state,
            ledger=_fresh_ledger(),
            attempts_used=0,
            policy=RecoveryPolicy(),
            reason="not a failure",
        )
        assert plan.action is RecoveryAction.NONE
        assert plan.reason == "not a failure"


def test_restart_when_no_fresh_recovery_evidence() -> None:
    """A ledger with no FILESYSTEM-precedence datum means no usable evidence:
    the ladder restarts from a clean context rather than trusting memory."""
    ledger = EvidenceLedger(
        observed_at=ISO,
        entries=(
            Evidence.declare(
                source=EvidenceSource.AGENT_MEMORY,
                summary="worker recollection only",
                observed_at=ISO,
            ),
        ),
    )
    plan = decide_recovery(
        state=LifecycleState.FAILED,
        ledger=ledger,
        attempts_used=0,
        policy=RecoveryPolicy(max_attempts=3, rollback_available=True),
        reason="no fresh datum",
    )
    assert plan.action is RecoveryAction.RESTART
    assert plan.attempts_used == 0


def test_retry_with_fresh_filesystem_evidence() -> None:
    """Fresh FILESYSTEM evidence + attempts below max -> symmetric RETRY."""
    plan = decide_recovery(
        state=LifecycleState.FAILED,
        ledger=_fresh_ledger(),
        attempts_used=2,
        policy=RecoveryPolicy(max_attempts=3, rollback_available=True),
        reason="post-PASS mutation datum outranks worker PASS claim",
    )
    assert plan.action is RecoveryAction.RETRY
    assert plan.attempts_used == 2


def test_rollback_when_attempts_exhausted_and_available() -> None:
    """Max attempts reached + a sealed last-known-good blob -> ROLLBACK."""
    plan = decide_recovery(
        state=LifecycleState.FAILED,
        ledger=_fresh_ledger(),
        attempts_used=3,
        policy=RecoveryPolicy(max_attempts=3, rollback_available=True),
        reason="recovery attempts exhausted",
    )
    assert plan.action is RecoveryAction.ROLLBACK
    assert plan.attempts_used == 3
    assert plan.creator_gated is False


def test_hold_when_exhausted_and_no_rollback_datum() -> None:
    """Exhausted + no rollback blob -> HOLD for the creator, creator-gated."""
    plan = decide_recovery(
        state=LifecycleState.FAILED,
        ledger=_fresh_ledger(),
        attempts_used=3,
        policy=RecoveryPolicy(max_attempts=3, rollback_available=False),
        reason="no rollback datum",
    )
    assert plan.action is RecoveryAction.HOLD
    assert plan.creator_gated is True


def test_escalate_when_exceeded_and_escalate_after_reached() -> None:
    """escalate_after (explicitly injected, never ambient) promotes to L2."""
    plan = decide_recovery(
        state=LifecycleState.FAILED,
        ledger=_fresh_ledger(),
        attempts_used=3,
        policy=RecoveryPolicy(max_attempts=3, rollback_available=True, escalate_after=3),
        reason="recovery exceeded; needs creator ruling",
    )
    assert plan.action is RecoveryAction.ESCALATE
    assert plan.creator_gated is True


def test_decision_is_a_deterministic_fold() -> None:
    """Same inputs -> same plan object values, twice (fold-stability F-M2.3-6)."""
    args = dict(
        state=LifecycleState.FAILED,
        ledger=_fresh_ledger(),
        attempts_used=1,
        policy=RecoveryPolicy(max_attempts=3, rollback_available=True),
        reason="fresh evidence; symmetric retry",
    )
    a = decide_recovery(**args)
    b = decide_recovery(**args)
    assert a.action is b.action
    assert a == b
    assert isinstance(a, RecoveryPlan)


def test_recovery_policy_defaults_are_bounded_and_hermetic() -> None:
    """max_attempts defaults to 3 (bounded repair); escalate_after defaults to
    None so non-local escalation is NEVER ambient."""
    p = RecoveryPolicy()
    assert p.max_attempts == 3
    assert p.rollback_available is False
    assert p.escalate_after is None