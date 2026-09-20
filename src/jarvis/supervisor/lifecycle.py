from __future__ import annotations

"""Task lifecycle ratchet - the FROZEN_SUCCESS state (M2.5, spec 84.4).

The lifecycle is the SAME kind of deterministic gate the M2.3/M2.4 writer
already ratchets with (fold-stability precedent, F-M2.3-6 / F-M2.4-6
re-applied): every transition is a DECLARED DATUM, never a code branch. The
ratchet law, re-sealed for M2.5:

    once a task reaches PASS (its acceptance criteria green and
    independently re-verified), it enters FROZEN_SUCCESS - a TERMINAL,
    ABSORBING state. From FROZEN_SUCCESS there is exactly ONE outgoing edge
    in the whole ladder: creator-gated REOPEN (a NEW creator task that
    explicitly reopens the package). No worker edit, refactor, additional
    test, or "one final improvement" may move a FROZEN_SUCCESS datum. That is
    the hard stop the M2.4 drift failure demanded (T18 regression).

Determinism: same transition table + same current state + same event gives
IDENTICAL next state - the table IS the decision, not an approximation of it.
Clocks/randomness/ambient reads are injected seams, never ambient (hermetic
default, kickoff item E / 84.4 precedent); this module reads NO model state
and performs NO effects.
"""


import enum
from dataclasses import dataclass, field
from typing import Literal, Mapping


class LifecycleState(str, enum.Enum):
    """Declared states a ratchet may occupy (data, not branches).

    FROZEN_SUCCESS is ABSORBING by construction - the only declared edge out
    of it is REOPEN, and REOPEN is creator-gated (L2 authority, 84.4 ladder).
    """

    PROPOSED = "proposed"
    IMPLEMENTING = "implementing"
    WORKER_VERIFY = "worker_verify"
    PASS = "pass"
    FROZEN_SUCCESS = "frozen_success"
    FAILED = "failed"
    REPAIRING = "repairing"
    ESCALATED = "escalated"
    HELD = "held"


class LifecycleEvent(str, enum.Enum):
    """Declared events that MAY move a ratchet (all else is rejected)."""

    TASK_APPROVED = "task_approved"
    EDIT_START = "edit_start"
    WORKER_CLAIM_PASS = "worker_claim_pass"
    INDEPENDENT_VERIFY_PASS = "independent_verify_pass"
    INDEPENDENT_VERIFY_FAIL = "independent_verify_fail"
    FREEZE = "freeze"
    MUTATION_DETECTED = "mutation_detected"
    REPAIR_ATTEMPT = "repair_attempt"
    RECOVERY_EXHAUSTED = "recovery_exhausted"
    EPISTEMIC_CONFLICT = "epistemic_conflict"
    STALLED = "stalled"
    CREATOR_ESCALATE = "creator_escalate"
    CREATOR_RULING = "creator_ruling"
    REOPEN = "reopen"


@dataclass(frozen=True)
class LifecycleTransition:
    """A single declared transition datum: (from, event) -> to + gating.

    `creator_gated=True` means ONLY the creator may authorize this edge; a
    worker can never move it. This is the entire authority model - a DATUM,
    not a code permission (84.4 data-not-branches precedent).
    """

    state: LifecycleState
    event: LifecycleEvent
    to: LifecycleState
    creator_gated: bool = False


def _transitions() -> frozenset[LifecycleTransition]:
    t = LifecycleTransition
    s = LifecycleState
    e = LifecycleEvent
    return frozenset(
        {
            # proposal to work
            t(s.PROPOSED, e.TASK_APPROVED, s.IMPLEMENTING),
            t(s.PROPOSED, e.STALLED, s.HELD),
            # implementation
            t(s.IMPLEMENTING, e.EDIT_START, s.IMPLEMENTING),
            t(s.IMPLEMENTING, e.MUTATION_DETECTED, s.REPAIRING),
            t(s.IMPLEMENTING, e.REPAIR_ATTEMPT, s.REPAIRING),
            t(s.IMPLEMENTING, e.WORKER_CLAIM_PASS, s.WORKER_VERIFY),
            # worker verification - the actor may claim PASS but may NOT
            # freeze; freezing requires INDEPENDENT verification.
            t(s.WORKER_VERIFY, e.INDEPENDENT_VERIFY_PASS, s.PASS),
            t(s.WORKER_VERIFY, e.INDEPENDENT_VERIFY_FAIL, s.FAILED),
            t(s.WORKER_VERIFY, e.EPISTEMIC_CONFLICT, s.ESCALATED),
            t(s.WORKER_VERIFY, e.EDIT_START, s.IMPLEMENTING),
            # PASS -> FROZEN_SUCCESS: the ratchet seal. Absorbing.
            t(s.PASS, e.FREEZE, s.FROZEN_SUCCESS),
            # FAILED may be repaired or held
            t(s.FAILED, e.REPAIR_ATTEMPT, s.REPAIRING),
            t(s.FAILED, e.RECOVERY_EXHAUSTED, s.HELD),
            t(s.FAILED, e.CREATOR_ESCALATE, s.ESCALATED),
            # REPAIRING
            t(s.REPAIRING, e.EDIT_START, s.IMPLEMENTING),
            t(s.REPAIRING, e.RECOVERY_EXHAUSTED, s.FAILED),
            # ESCALATED may only move on CREATOR_RULING (L2)
            t(s.ESCALATED, e.CREATOR_RULING, s.IMPLEMENTING),
            t(s.ESCALATED, e.CREATOR_RULING, s.FAILED),
            t(s.ESCALATED, e.CREATOR_RULING, s.HELD),
            # HELD may only move on CREATOR_RULING (L2)
            t(s.HELD, e.CREATOR_RULING, s.IMPLEMENTING),
            t(s.HELD, e.CREATOR_RULING, s.FAILED),
            # THE ONLY FROZEN_SUCCESS edge: creator-gated REOPEN.
            # A worker can never take it. This is the hard stop.
            t(s.FROZEN_SUCCESS, e.REOPEN, s.IMPLEMENTING, creator_gated=True),
        }
    )


lifecycle_transitions: frozenset[LifecycleTransition] = _transitions()


@dataclass(frozen=True)
class LifecycleDecision:
    """Outcome of consulting the table: the next state, or a rejection."""

    current: LifecycleState
    event: LifecycleEvent
    next_state: LifecycleState | None
    transition: LifecycleTransition | None
    reason: str = ""
    rejected: bool = False


def _lookup(state: LifecycleState, event: LifecycleEvent) -> LifecycleTransition | None:
    for tr in lifecycle_transitions:
        if tr.state == state and tr.event == event:
            return tr
    return None


def lifecycle_decision(
    state: LifecycleState, event: LifecycleEvent
) -> LifecycleDecision:
    """Pure deterministic lookup: same (state, event) -> same decision.

    This is the WHOLE transition engine - no branches on content, no ambient
    reads, no clock. The table IS the datum.
    """
    tr = _lookup(state, event)
    if tr is None:
        return LifecycleDecision(
            current=state,
            event=event,
            next_state=None,
            transition=None,
            reason=f"no declared transition for {state.value} -[{event.value}]",
            rejected=True,
        )
    return LifecycleDecision(
        current=state,
        event=event,
        next_state=tr.to,
        transition=tr,
    )


@dataclass(frozen=True)
class TaskLifecycle:
    """The ratchet; immutable. Every apply() returns a NEW rung."""

    state: LifecycleState = LifecycleState.PROPOSED

    def apply(self, event: LifecycleEvent) -> "TaskLifecycle":
        decision = lifecycle_decision(self.state, event)
        if decision.rejected or decision.next_state is None:
            # Rejected events leave state UNCHANGED (ratchet-safe: a worker
            # that cannot move simply cannot move - there is no "contingency
            # branch" that reopens a frozen package).
            return self
        if decision.transition is not None and decision.transition.creator_gated:
            # creator-gated edges are returned as-is by the table below, but
            # a non-creator caller receiving this decision is told REJECTED.
            return self
        return TaskLifecycle(state=decision.next_state)

    def declared_transition(
        self, event: LifecycleEvent, *, as_creator: bool
    ) -> LifecycleDecision:
        """Consult the table WITH authority metadata; creator edges visible
        only when `as_creator=True` (L2 gate lifted by the creator only)."""
        decision = lifecycle_decision(self.state, event)
        if (
            decision.transition is not None
            and decision.transition.creator_gated
            and not as_creator
        ):
            return LifecycleDecision(
                current=self.state,
                event=event,
                next_state=None,
                transition=decision.transition,
                reason="creator-gated edge; worker cannot move it",
                rejected=True,
            )
        return decision

    @property
    def frozen_success(self) -> bool:
        return self.state is LifecycleState.FROZEN_SUCCESS
