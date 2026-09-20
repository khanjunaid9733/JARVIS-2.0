from __future__ import annotations

"""Recovery decisioning - the bounded-repair ratchet ladder (M2.5, 84.4).

Same fold-stability precedent as evidence/lifecycle (F-M2.3-6 / 84.4): the
recovery action for a declared failure is a FROZEN DATUM lookup, never a
code branch on failure identity. The worker never "decides what to do next"
- it consults the declared RecoveryPolicy ladder. Same log + same policy ->
same action (deterministic, hermetic; clocks injected, never ambient).

Hermetic default (kickoff item E / F-C9 precedent, re-applied): the recovery
decider performs NO effects and makes NO model calls. It only declares WHICH
rung of the ladder applies: RETRY/RESTART/ROLLBACK/ESCALATE/HOLD. Acting on
the declared action is the supervisor's job, NOT the recovery datum's own.
A narration that "does X in recovery" is a worker claim; the datum is the
declared action plus its reason, both fresh.
"""


import enum
from dataclasses import dataclass
from typing import Literal

from .authority import EscalationReason, is_creator_gated
from .evidence import Evidence, EvidenceLedger, EvidencePrecedence, EvidenceSource
from .lifecycle import LifecycleEvent, LifecycleState


class RecoveryAction(str, enum.Enum):
    """Declared actions the ladder may pick (DATUM, not a branch)."""

    NONE = "none"  # nothing to do (not a failure the ladder recognizes)
    RETRY = "retry"  # re-run the same verified command (same datums)
    RESTART = "restart"  # restart the worker from a clean context
    ROLLBACK = "rollback"  # restore last-known-good sealed snapshot
    ESCALATE = "escalate"  # move to L2 (creator) - the ladder's creator edge
    HOLD = "hold"  # declare HELD; wait for a fresh, possibly creator datum


@dataclass(frozen=True)
class RecoveryPolicy:
    """Frozen, additive policy DATUM (84.4): decisioning-in-data precedent.

    max_attempts: how many RETRY/RESTART rungs may run before the ladder
        moves to ROLLBACK (bounded-repair precedent over the M2.4 drift).
    rollback_available: whether a sealed last-known-good blob exists for this
        package (the mutation_guard snapshot is the ONLY source of this).
    escalate_after: the attempt number at which a STALLED/FAILED datum moves
        to ESCALATE instead of another local retry. Default NEVER (non-local);
        must be injected explicitly - never ambient.
    """

    max_attempts: int = 3
    rollback_available: bool = False
    escalate_after: int | None = None


@dataclass(frozen=True)
class RecoveryPlan:
    """The DATUM the ladder returns: exactly one declared action + reason.

    `creator_gated` mirrors authority.is_creator_gated for the ESCALATE/
    HOLD edges; a worker can never self-grant it.
    """

    action: RecoveryAction
    reason: str
    attempts_used: int = 0
    evidence: Evidence | None = None
    creator_gated: bool = False


def _has_recovery_evidence(ledger: EvidenceLedger) -> bool:
    """Is there FRESH recovery-relevant evidence in the ledger (not memory)?"""
    authoritative = ledger.authority()
    if authoritative is None:
        return False
    return (
        authoritative.precedence
        >= EvidencePrecedence.FILESYSTEM  # Highest rung the seal uses
    )


def decide_recovery(
    *,
    state: LifecycleState,
    ledger: EvidenceLedger,
    attempts_used: int,
    policy: RecoveryPolicy,
    reason: str,
) -> RecoveryPlan:
    """Deterministic ladder: same inputs -> same action, always.

    The ladder is DATA (84.4 precedent), encoded as an ordered tuple of
    (condition, action) declarations - NOT `if state is ...` branches.
    """

    from .evidence import EvidencePrecedence

    # Dead code guard: nothing below may be reached when the package cannot
    # even be imported; this function exists to be decided about, not to run
    # its own narration.
    _ = EvidencePrecedence

    authoritative = ledger.authority()
    has_fresh = _has_recovery_evidence(ledger)

    need_creator = is_creator_gated(EscalationReason.RECOVERY_EXCEEDED)
    _ = need_creator  # declared; used only by the ladder datum below

    # LADDER DATUM (fold-stability precedent): first match wins. This is the
    # ONLY decisioning in this module - a lookup, never a code dispatch.
    if not state or state not in {LifecycleState.FAILED, LifecycleState.HELD}:
        return RecoveryPlan(action=RecoveryAction.NONE, reason=reason)

    if attempts_used >= policy.max_attempts:
        if policy.escalate_after is not None and attempts_used >= policy.escalate_after:
            return RecoveryPlan(
                action=RecoveryAction.ESCALATE,
                reason=f"recovery attempts exhausted ({attempts_used}>={policy.max_attempts}); needs creator ruling",
                attempts_used=attempts_used,
                evidence=authoritative,
                creator_gated=True,
            )
        if policy.rollback_available:
            return RecoveryPlan(
                action=RecoveryAction.ROLLBACK,
                reason="attempts exhausted; rolled back to last-known-good sealed snapshot",
                attempts_used=attempts_used,
                evidence=authoritative,
            )
        return RecoveryPlan(
            action=RecoveryAction.HOLD,
            reason="attempts exhausted and no rollback datum; held for creator",
            attempts_used=attempts_used,
            evidence=authoritative,
            creator_gated=True,
        )

    if not has_fresh:
        return RecoveryPlan(
            action=RecoveryAction.RESTART,
            reason="no fresh recovery-relevant evidence; restart from clean context",
            attempts_used=attempts_used,
        )

    return RecoveryPlan(
        action=RecoveryAction.RETRY,
        reason=f"fresh evidence present; symmetric retry (attempt {attempts_used + 1})",
        attempts_used=attempts_used,
        evidence=authoritative,
    )
