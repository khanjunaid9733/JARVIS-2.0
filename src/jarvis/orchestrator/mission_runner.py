from __future__ import annotations

"""Multi-step mission execution loop (M3.2, spec 84.4 ratchet, re-applied).

The runner is the ORCHESTRATION plane: it folds a DECLARED ordered mission
plan through the SAME frozen supervisor datums turn by turn. It introduces NO
new state machine and NO new authority - per step it drives a fresh
TaskLifecycle through the exact declared transitions (TASK_APPROVED ->
IMPLEMENTING -> WORKER_VERIFY), then lets ONLY an injected INDEPENDENT
verifier seam (never the worker) move the ratchet to PASS, then FREEZE to
FROZEN_SUCCESS. A fail always returns to the supervisor's recovery ladder
(RETRY / RESTART / ROLLBACK / ESCALATE / HOLD), bounded by RecoveryPolicy.

Determinism (F-M2.3-6 / F-M2.4-6 fold-stability precedent, re-applied): same
plan + same policy + same injected verifier datum + same observed_at gives
IDENTICAL step results and an IDENTICAL MissionRun, always. There is no
ambient state: no clocks, no randomness, no process calls, no model calls -
on the SHIPPED default the runner is hermetic (kickoff E / 84.4 precedent).

Multi-worker / role-split law (re-applied): the worker NEVER provides the
verification datum. `StepVerifier` is a separate injected role; a worker
claim (AGENT_MEMORY) can never set a true value, and only a verifier datum
with executable authority (FILESYSTEM / FRESH_VERIFIER) may move the ratchet
to PASS. `Decomposer` is likewise an OPT-IN adapter seam: autonomous task
decomposition is a proposal-plane capability and is NEVER invoked implicitly
by the runner's fold (model proposes; determinism disposes).

Additive law (M2.3/M2.4/M2.5 precedent, re-applied): this package is STRICTLY
additive. Nothing below lives in a frozen module; no frozen module is
import-modified or touched. New task, new package.
"""


from dataclasses import dataclass
from typing import Protocol

from jarvis.supervisor import (
    EvidenceLedger,
    EvidenceSource,
    LifecycleEvent,
    LifecycleState,
    RecoveryAction,
    RecoveryPlan,
    RecoveryPolicy,
    TaskLifecycle,
    VerificationResult,
    decide_recovery,
)

@dataclass(frozen=True)
class MissionStep:
    """One declared, ordered substep of a mission plan (a datum, not a branch).

    `id` is the stable identity used for step-by-step acceptance (aka the
    unit `scripts/verify.py` is asked to re-verify); `summary` is narration
    only and carries no authority.
    """

    id: str
    summary: str


@dataclass(frozen=True)
class MissionPlan:
    """The declared ordered mission datum the runner folds over.

    `steps` is ORDERED: the runner executes strictly sequentially and stops
    at the first step that cannot reach FROZEN_SUCCESS in bounded repair.
    `policy` is the frozen RecoveryPolicy ladder for every step.
    """

    id: str
    steps: tuple[MissionStep, ...]
    policy: RecoveryPolicy = RecoveryPolicy()

    @classmethod
    def declared(
        cls, plan_id: str, steps: tuple[MissionStep, ...]
    ) -> "MissionPlan":
        return cls(id=plan_id, steps=steps)

    def __len__(self) -> int:
        return len(self.steps)


class StepVerifier(Protocol):
    """The INDEPENDENT verification seam for a single mission step.

    Runs FRESH and returns a machine datum (exit code + output). It is NEVER
    the worker: a worker's claim of PASS is never handed to the ratchet as
    verification; this seam is. Same seam + same step -> same datum.
    """

    def verify(self, step: MissionStep) -> VerificationResult: ...


class Decomposer(Protocol):
    """Proposal-plane seam (OPT-IN, never ambient): turn a high-level goal
    into an ordered tuple of MissionSteps.

    The deterministic fold NEVER calls this silently. Decomposition is model-
    proposed proposal, disposed of by the plan's declared order.
    """

    def decompose(self, goal: str) -> tuple[MissionStep, ...]: ...


@dataclass(frozen=True)
class MissionStepResult:
    """The per-step outcome datum of one fold position in a MissionRun."""

    step: MissionStep
    attempts_used: int
    final_state: LifecycleState
    recovery: RecoveryPlan | None = None
    reason: str = ""

    @property
    def accepted(self) -> bool:
        return self.final_state is LifecycleState.FROZEN_SUCCESS


@dataclass(frozen=True)
class MissionRun:
    """The full deterministic fold result.

    `steps` preserves the DECLARED order and terminates at the first step
    that cannot reach FROZEN_SUCCESS in bounded repair (later steps are NOT
    executed - the mission halts at the first creator-gated / rolled-back /
    exhausted datum).
    """

    plan_id: str
    steps: tuple[MissionStepResult, ...]
    outcome: str  # ACCEPTED / HELD / ESCALATED / ROLLED_BACK

    @property
    def accepted(self) -> bool:
        return self.outcome == "ACCEPTED"

    @property
    def halted(self) -> bool:
        return not self.accepted

    @property
    def last(self) -> MissionStepResult | None:
        return self.steps[-1] if self.steps else None


class MissionRunner:
    """The deterministic mission fold. Same datums -> same run, always."""

    def _to_worker_verify(self) -> TaskLifecycle:
        """Drive a fresh ratchet to the point where only the independent
        verifier seam may move it (PROPOSED -> IMPLEMENTING -> WORKER_VERIFY)."""
        return (
            TaskLifecycle()
            .apply(LifecycleEvent.TASK_APPROVED)
            .apply(LifecycleEvent.WORKER_CLAIM_PASS)
        )

    def _fold_step(
        self,
        step: MissionStep,
        verifier: StepVerifier,
        observed_at: str,
        policy: RecoveryPolicy,
    ) -> MissionStepResult:
        lc = self._to_worker_verify()
        attempts = 0
        while True:
            fresh = verifier.verify(step)
            attempts += 1

            if fresh.value and fresh.source in (
                EvidenceSource.FILESYSTEM,
                EvidenceSource.FRESH_VERIFIER,
            ):
                lc = lc.apply(LifecycleEvent.INDEPENDENT_VERIFY_PASS)
                lc = lc.apply(LifecycleEvent.FREEZE)
                return MissionStepResult(
                    step=step,
                    attempts_used=attempts,
                    final_state=lc.state,
                    reason="independent verification passed; FROZEN_SUCCESS",
                )

            lc = lc.apply(LifecycleEvent.INDEPENDENT_VERIFY_FAIL)
            ledger = EvidenceLedger(
                observed_at=observed_at,
                entries=(fresh.evidence,),
            )
            plan = decide_recovery(
                state=lc.state,
                ledger=ledger,
                attempts_used=attempts,
                policy=policy,
                reason=f"step {step.id} failed independent verification",
            )
            if plan.action is RecoveryAction.RETRY:
                lc = (
                    lc.apply(LifecycleEvent.REPAIR_ATTEMPT)
                    .apply(LifecycleEvent.EDIT_START)
                    .apply(LifecycleEvent.WORKER_CLAIM_PASS)
                )
                continue
            if plan.action is RecoveryAction.RESTART:
                lc = self._to_worker_verify()
                continue

            # Terminal: ROLLBACK leaves the step FAILED (mission rolls back to
            # last-known-good); ESCALATE / HOLD ratchet to their declared L2
            # states. The mission halts on any of these.
            if plan.action is RecoveryAction.ESCALATE:
                lc = lc.apply(LifecycleEvent.CREATOR_ESCALATE)
            elif plan.action in (RecoveryAction.HOLD, RecoveryAction.NONE):
                lc = lc.apply(LifecycleEvent.RECOVERY_EXHAUSTED)
            return MissionStepResult(
                step=step,
                attempts_used=attempts,
                final_state=lc.state,
                recovery=plan,
                reason=plan.reason,
            )

    def run(
        self,
        *,
        plan: MissionPlan,
        verifier: StepVerifier,
        observed_at: str,
    ) -> MissionRun:
        results: list[MissionStepResult] = []
        policy = plan.policy
        for step in plan.steps:
            result = self._fold_step(step, verifier, observed_at, policy)
            results.append(result)
            if not result.accepted:
                return self._finish(plan.id, tuple(results))
        return self._finish(plan.id, tuple(results))

    def decompose_and_run(
        self,
        *,
        goal: str,
        decomposer: Decomposer,
        verifier: StepVerifier,
        observed_at: str,
    ) -> MissionRun:
        """OPT-IN proposal-plane entry: decompose (injected), then fold.

        `decomposer` and `verifier` are BOTH injected roles - neither is ever
        ambient. Decomposition strictly precedes, and never supervises, the
        deterministic fold.
        """
        steps = decomposer.decompose(goal)
        return self.run(
            plan=MissionPlan.declared(plan_id=goal, steps=steps),
            verifier=verifier,
            observed_at=observed_at,
        )

    @staticmethod
    def _finish(plan_id: str, results: tuple[MissionStepResult, ...]) -> MissionRun:
        if not results or all(r.accepted for r in results):
            return MissionRun(plan_id=plan_id, steps=results, outcome="ACCEPTED")
        last = results[-1]
        if last.final_state is LifecycleState.ESCALATED:
            return MissionRun(plan_id=plan_id, steps=results, outcome="ESCALATED")
        if last.final_state is LifecycleState.HELD:
            return MissionRun(plan_id=plan_id, steps=results, outcome="HELD")
        if last.recovery is None or last.recovery.action is RecoveryAction.ROLLBACK:
            return MissionRun(plan_id=plan_id, steps=results, outcome="ROLLED_BACK")
        return MissionRun(plan_id=plan_id, steps=results, outcome="HELD")


__all__ = [
    "Decomposer",
    "MissionPlan",
    "MissionRun",
    "MissionRunner",
    "MissionStep",
    "MissionStepResult",
    "StepVerifier",
]