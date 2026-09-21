from __future__ import annotations

"""M2.5 - the authority escalation ladder (84.4): tiers are DATA.

Authority is a declared `EscalationReason -> AuthorityTier` ladder, never code
dispatch on identity. L0 settles autonomously (STALLED); L1 is routine work
(CONTEXT_DRIFT, MUTATION_DETECTED) with re-verified evidence; L2 is
CREATOR-ONLY: FROZEN_CONFLICT, SPEC_AMBIGUITY, AUTHORITY_CHANGE,
IRREVERSIBLE, MERGE_PUSH, RECOVERY_EXCEEDED. Same reason -> same tier, always.
Hermetic: pure lookup, no state, no clock, no narration.
"""

import enum

import pytest

from jarvis.supervisor import (
    AuthorityTier,
    EscalationReason,
    decide_authority_tier,
    is_creator_gated,
)

# The declared ladder - DATA, from authority.py's _LADDER.
EXPECTED_LADDER: dict[EscalationReason, AuthorityTier] = {
    EscalationReason.FROZEN_CONFLICT: AuthorityTier.L2,
    EscalationReason.SPEC_AMBIGUITY: AuthorityTier.L2,
    EscalationReason.AUTHORITY_CHANGE: AuthorityTier.L2,
    EscalationReason.IRREVERSIBLE: AuthorityTier.L2,
    EscalationReason.MERGE_PUSH: AuthorityTier.L2,
    EscalationReason.RECOVERY_EXCEEDED: AuthorityTier.L2,
    EscalationReason.CONTEXT_DRIFT: AuthorityTier.L1,
    EscalationReason.MUTATION_DETECTED: AuthorityTier.L1,
    EscalationReason.STALLED: AuthorityTier.L0,
}


def test_ladder_has_exactly_three_tiers_and_nine_reasons() -> None:
    assert list(AuthorityTier) == [AuthorityTier.L0, AuthorityTier.L1, AuthorityTier.L2]
    assert [r for r in EscalationReason] == list(EscalationReason)
    assert len(EXPECTED_LADDER) == 9


def test_creator_gated_is_exactly_the_l2_set() -> None:
    """Only L2 reasons cross the creator seam; L1/L0 never do."""
    for reason, tier in EXPECTED_LADDER.items():
        assert decide_authority_tier(reason) is tier
        assert is_creator_gated(reason) is (tier is AuthorityTier.L2)


@pytest.mark.parametrize("reason", list(EscalationReason))
def test_ladder_is_deterministic_data(reason: EscalationReason) -> None:
    """Same reason -> same tier on every consultation (pure lookup, 84.4)."""
    assert decide_authority_tier(reason) is EXPECTED_LADDER[reason]
    assert decide_authority_tier(reason) is decide_authority_tier(reason)


def test_l0_settles_without_creator() -> None:
    assert decide_authority_tier(EscalationReason.STALLED) is AuthorityTier.L0
    assert is_creator_gated(EscalationReason.STALLED) is False


def test_l1_is_routine_and_not_creator_gated() -> None:
    for reason in (EscalationReason.CONTEXT_DRIFT, EscalationReason.MUTATION_DETECTED):
        assert decide_authority_tier(reason) is AuthorityTier.L1
        assert is_creator_gated(reason) is False


def test_l2_crosses_the_creator_seam_only() -> None:
    for reason, tier in EXPECTED_LADDER.items():
        if tier is AuthorityTier.L2:
            assert is_creator_gated(reason) is True
            assert reason.value is not None  # declared datum, not a ghost


def test_merge_push_is_ratchet_sealed_to_creator() -> None:
    """I7: merge/push can NEVER be decided by the agent itself."""
    assert decide_authority_tier(EscalationReason.MERGE_PUSH) is AuthorityTier.L2
    assert is_creator_gated(EscalationReason.MERGE_PUSH) is True


def test_reason_is_a_str_enum_datum_not_a_role() -> None:
    """Authority is DATA: the reason serializes to its declared string, and
    tiers are comparable ints (L0 < L1 < L2)."""
    assert isinstance(EscalationReason.FROZEN_CONFLICT, enum.Enum)
    assert EscalationReason.FROZEN_CONFLICT.value == "frozen_conflict"
    assert AuthorityTier.L0 < AuthorityTier.L1 < AuthorityTier.L2