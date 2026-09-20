from __future__ import annotations

"""Delegated authority datum for the supervisor (M2.5, spec 84.4).

Authority is DATA, not roles: the tier a given decision escalates to is
declared by a frozen `EscalationReason -> AuthorityTier` LADDER datum, never
by code dispatch on identity (precedent F-M2.3-6 / kickoff item B). The
creator-set of reasons (frozen conflict, spec ambiguity, authority change,
irreversible action, merge/push) is the ONLY set that reaches the creator;
everything else is settled at the lowest rung the evidence supports.

Determinism: `decide_authority_tier(reason)` is a pure lookup - same reason,
same tier, always. No ambient state, no clock, no narration.
"""

import enum
from typing import Literal


class AuthorityTier(enum.IntEnum):
    """Lower numeric tier settles more of the operation autonomously.

    L0 - fully deterministic, zero narration required (the frozen gate itself
         already decides: Same log + same policy -> same result).
    L1 - routine/routine-datum decisions: worker may act within a declared
         policy, evidence is re-verified fresh before accepting PASS.
    L2 - CREATOR-ONLY: frozen conflict, spec ambiguity, authority change,
         irreversible action, merge/push. Nothing in L2 may be decided by the
         agent, its narration, or its memory - it is RATCHET-sealed to the
         creator (M2.2 done-gate precedent).
    """

    L0 = 0
    L1 = 1
    L2 = 2


class EscalationReason(str, enum.Enum):
    """Declared reasons. Only L2 reasons cross the creator seam."""

    FROZEN_CONFLICT = "frozen_conflict"
    SPEC_AMBIGUITY = "spec_ambiguity"
    AUTHORITY_CHANGE = "authority_change"
    IRREVERSIBLE = "irreversible"
    MERGE_PUSH = "merge_push"
    CONTEXT_DRIFT = "context_drift"
    STALLED = "stalled"
    MUTATION_DETECTED = "mutation_detected"
    RECOVERY_EXCEEDED = "recovery_exceeded"


_CREATOR_GATED: frozenset[EscalationReason] = frozenset(
    {
        EscalationReason.FROZEN_CONFLICT,
        EscalationReason.SPEC_AMBIGUITY,
        EscalationReason.AUTHORITY_CHANGE,
        EscalationReason.IRREVERSIBLE,
        EscalationReason.MERGE_PUSH,
    }
)

# LADDER datum (84.4 precedent): the reason -> tier mapping is DATA.
_LADDER: dict[EscalationReason, AuthorityTier] = {
    EscalationReason.FROZEN_CONFLICT: AuthorityTier.L2,
    EscalationReason.SPEC_AMBIGUITY: AuthorityTier.L2,
    EscalationReason.AUTHORITY_CHANGE: AuthorityTier.L2,
    EscalationReason.IRREVERSIBLE: AuthorityTier.L2,
    EscalationReason.MERGE_PUSH: AuthorityTier.L2,
    EscalationReason.CONTEXT_DRIFT: AuthorityTier.L1,
    EscalationReason.STALLED: AuthorityTier.L0,
    EscalationReason.MUTATION_DETECTED: AuthorityTier.L1,
    EscalationReason.RECOVERY_EXCEEDED: AuthorityTier.L2,
}


def decide_authority_tier(reason: EscalationReason) -> AuthorityTier:
    """Pure ladder lookup: same reason -> same tier (deterministic)."""
    return _LADDER[reason]


def is_creator_gated(reason: EscalationReason) -> bool:
    """True only for the RATCHET-sealed creator set (never narrated)."""
    return decide_authority_tier(reason) == AuthorityTier.L2
