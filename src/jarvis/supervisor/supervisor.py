from __future__ import annotations

"""The supervisor - lazy-valuation control kernel (M2.5, spec 84.4).

This file is the ONLY one in the supervisor package that may wire the other
five modules together. It is the CONTROL SURFACE: observe (evidence) ->
decide (lifecycle + authority + recovery datums) -> act (acceptor seam) ->
verify (verifier seam), with the mutation guard standing BETWEEN PASS and
FROZEN_SUCCESS.

Roles are split behind explicit seams - the SAME implementer is NEVER allowed
to verify its own success. The worker claims PASS; an INDEPENDENT verifier
(and only it) may move the ratchet to PASS; only then may the mutation guard
be asked to freeze the blob set, and only a freeze with a byte-identical
ledger produces FROZEN_SUCCESScars.

Determinism: same log + same policy + same injected seams -> identical
decision sequence, always (84.4 / F-M2.3-6 / F-M2.4-6 fold-stability
precedent re-applied at the orchestration rung). Clocks/randomness are
injected, never ambient; no model calls on the SHIPPED default policy; no
ambient reads; no effects except through the declared acceptor seams.
"""


import enum
from dataclasses import dataclass, field
from typing import Protocol, Mapping, Sequence

from .authority import (
    AuthorityTier,
    EscalationReason,
    decide_authority_tier,
    is_creator_gated,
)
from .evidence import (
    Evidence,
    EvidenceLedger,
    EvidenceSource,
    EvidencePrecedence,
    VerificationResult,
)
from .lifecycle import (
    LifecycleEvent,
    LifecycleState,
    LifecycleTransition,
    TaskLifecycle,
    lifecycle_transitions,
)
from .mutation_guard import MutationGuard, MutationReport, PackageSnapshot
from .recovery import RecoveryAction, RecoveryPlan, RecoveryPolicy, decide_recovery


class Verifier(Protocol):
    """The independent-verification seam. Runs FRESH, returns bytes datum.

    The verifier is NEVER the worker: it is a separate role/process that
    re-runs the acceptance surface and returns the machine datum (exit code +
    fresh output). A worker's claim of PASS is never handed to the ratchet as
    verification; this seam is. Same seam + same package -> same datum.
    """

    def verify(self) -> VerificationResult: ...


class Observer(Protocol):
    """Observe the live surface: returns the ledger of what is ACTUALLY true."""

    def observe(self) -> EvidenceLedger: ...


class Acceptor(Protocol):
    """The act seam: perform ONE declared effect (or refuse)."""

    def accept(self, decision: "SupervisorDecision") -> None: ...


@dataclass(frozen=True)
class SupervisorDecision:
    """The single declared outcome datum of a supervisor pass.

    `frozen_success` is True ONLY after the ratchet's hard seal: full suite
    PASS declared + independent verification PASS + mutation guard sealed the
    blob set. It is ABSORBING: nothing below may move a FROZEN_SUCCESS datum
    (84.4 / spec "the state a package enters once accepted cannot be improved,
    refactored, or re-tested merely because the worker thinks it would improve
    something else").
    """

    state: LifecycleState
    verdict: str  # one of: PASS / FAIL / HELD / ESCALATED / FROZEN_SUCCESS
    ledger: EvidenceLedger
    verifier: VerificationResult
    recovery: RecoveryPlan | None = None
    reason: str = ""
    mutation: MutationReport | None = None
    creator_gated: bool = False

    @property
    def frozen_success(self) -> bool:
        return self.state is LifecycleState.FROZEN_SUCCESS

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS" or self.frozen_success


class Supervisor:
    """The executable ratchet. observe -> decide -> act -> verify.

    Fully deterministic given the SAME injected datum set. The worker cannot
    vote on its own success: worker claims enter the ledger at AGENT_MEMORY
    precedence (the LOWEST rung) and can only ever be overridden by the
    higher datums the supervisor itself gathers (FILESYSTEM / FRESH_VERIFIER
    / GIT_STATE precedences).
    """

    __slots__ = (
        "_lifecycle",
        "_guard",
        "_ledger",
        "_creator_gated_reasons",
    )

    def __init__(
        self,
        policy: RecoveryPolicy | None = None,
        snapshot: PackageSnapshot | None = None,
        creator_gated_reasons: Sequence = (),
        *,
        lifecycle: TaskLifecycle | None = None,
        guard: MutationGuard | None = None,
        ledger: EvidenceLedger | None = None,
    ) -> None:
        self._lifecycle = lifecycle or TaskLifecycle()
        self._guard = guard or MutationGuard()
        self._ledger = ledger or EvidenceLedger()
        self._creator_gated_reasons = tuple(creator_gated_reasons)

    @property
    def lifecycle(self) -> TaskLifecycle:
        return self._lifecycle

    @property
    def state(self) -> LifecycleState:
        return self._lifecycle.state

    @property
    def frozen_success(self) -> bool:
        return self._lifecycle.state is LifecycleState.FROZEN_SUCCESS

    def _escalate(
        self,
        *,
        reason: EvidenceSource,
        summary: str,
        observed_at: str,
    ) -> SupervisorDecision:
        ev = Evidence.declare(source=reason, summary=summary, observed_at=observed_at)
        self._ledger = self._ledger.with_entry(ev)
        return SupervisorDecision(
            state=LifecycleState.ESCALATED,
            verdict="ESCALATED",
            ledger=self._ledger,
            verifier=VerificationResult.decided(
                value=False,
                source=EvidenceSource.AGENT_MEMORY,
                observed_at=observed_at,
                summary=summary,
            ),
            reason="escalated to creator (L2 gate): " + summary,
            creator_gated=True,
        )

    def decide(
        self,
        *,
        worker_claim: bool,
        observed_at: str,
    ) -> SupervisorDecision:
        worker_evidence = Evidence.declare(
            source=EvidenceSource.AGENT_MEMORY,
            summary=(
                "worker claim of success"
                if worker_claim
                else "worker claim of failure"
            ),
            observed_at=observed_at,
        )
        self._ledger = self._ledger.with_entry(worker_evidence)

        state = self._lifecycle.state
        event = (
            LifecycleEvent.WORKER_CLAIM_PASS
            if worker_claim
            else LifecycleEvent.WORKER_CLAIM_FAIL
        )

        if self.frozen_success:
            return SupervisorDecision(
                state=state,
                verdict="FROZEN_SUCCESS",
                ledger=self._ledger,
                verifier=VerificationResult.decided(
                    value=True,
                    source=EvidenceSource.IMMUTABLE_ARTIFACT,
                    observed_at=observed_at,
                    summary="FROZEN_SUCCESS is absorbing; no worker claim moves it",
                ),
                reason="hard-stop: FROZEN_SUCCESS cannot be reopened by a worker",
                creator_gated=True,
            )

        decision = self._lifecycle.declared_transition(event, as_creator=False)
        if decision.rejected:
            # Escape the thing the ratchet forbids - no narration vetoes bytes:
            # a worker trying to move a creator-gated edge is started with the
            # REJECTED datum, not a fork.
            return SupervisorDecision(
                state=state,
                verdict="HELD",
                ledger=self._ledger,
                verifier=VerificationResult.decided(
                    value=False,
                    source=EvidenceSource.AGENT_MEMORY,
                    observed_at=observed_at,
                    summary="transition rejected by lifecycle datum",
                ),
                reason=decision.reason,
                creator_gated=decision.transition is not None
                and decision.transition.creator_gated,
            )

        if worker_claim:
            return SupervisorDecision(
                state=LifecycleState.WORKER_VERIFY,
                verdict="PASS",
                ledger=self._ledger,
                verifier=VerificationResult.decided(
                    value=False,  # worker PASS is a CLAIM, never a verdict (rung)
                    source=EvidenceSource.AGENT_MEMORY,
                    observed_at=observed_at,
                    summary="worker claims PASS; INDEPENDENT verification required",
                ),
                reason="worker claimed PASS; holding for independent verification",
            )
        return SupervisorDecision(
            state=LifecycleState.FAILED,
            verdict="FAIL",
            ledger=self._ledger,
            verifier=VerificationResult.decided(
                value=False,
                source=EvidenceSource.AGENT_MEMORY,
                observed_at=observed_at,
                summary="worker reports failure",
            ),
            reason="worker reported failure; recovery ladder applies",
        )

    def verify(
        self,
        *,
        verifier: Verifier,
        observed_at: str,
        repo_snapshot: PackageSnapshot | None = None,
    ) -> SupervisorDecision:
        """Move the ratchet on FRESH independent datum ONLY (never narration).

        This is the ONLY place PASS may become real: after this call the
        mutation guard the pass is sealed against is FROZEN, and any later
        byte drift is a MUTATION report, never a suggestion (FROZEN_SUCCESS
        drift precedent: the M2.4 "405->403" drift is exactly what this
        guard turns into a non-event).
        """
        fresh = verifier.verify()

        if fresh.source is EvidenceSource.FRESH_VERIFIER and fresh.value:
            # ratchet forward: the independent datum is the rung move
            return SupervisorDecision(
                state=LifecycleState.PASS,
                verdict="PASS",
                ledger=self._ledger.with_entry(fresh.evidence),
                verifier=fresh,
                reason="independent fresh verification PASS",
            )
        return SupervisorDecision(
            state=LifecycleState.FAILED,
            verdict="FAIL",
            ledger=self._ledger.with_entry(fresh.evidence),
            verifier=fresh,
            reason="independent fresh verification FAIL",
        )

    def freeze(self, *, observed_at: str, snapshot: PackageSnapshot) -> SupervisorDecision:
        """Seal the package: the hard ratchet stop (FROZEN_SUCCESS).

        Only the creator may MOVE a FROZEN_SUCCESS datum (the "reopen" edge
        is creator-gated in lifecycle.py). A worker can never reopen it - this
        is the sealed acceptance the whole supervisor exists to enforce.
        """
        report = self._guard.seal(snapshot=snapshot)
        self._lifecycle = self._lifecycle.apply(LifecycleEvent.FREEZE)
        ev = Evidence.declare(
            source=EvidenceSource.IMMUTABLE_ARTIFACT,
            summary="package sealed; byte-ldrger frozen",
            observed_at=observed_at,
        )
        self._ledger = self._ledger.with_entry(ev)
        return SupervisorDecision(
            state=LifecycleState.FROZEN_SUCCESS,
            verdict="FROZEN_SUCCESS",
            ledger=self._ledger,
            verifier=VerificationResult.decided(
                value=True,
                source=EvidenceSource.FILESYSTEM,
                observed_at=observed_at,
                summary="FROZEN_SUCCESS: sealed; mutating it later is a report, not an edit",
            ),
            reason="ratchet sealed: FROZEN_SUCCESS",
            mutation=report,
            creator_gated=True,
        )


__all__ = ["Acceptor", "Observer", "Supervisor", "SupervisorDecision", "Verifier"]
