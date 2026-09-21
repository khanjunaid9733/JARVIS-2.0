from __future__ import annotations

"""Automated failure recovery & rollback engine (M3.4, spec 84.4 re-applied).

M3.2 declared WHICH recovery action applies (RETRY / RESTART / ROLLBACK /
ESCALATE / HOLD via the supervisor's `decide_recovery` ladder datum). M3.4 is
the ACT plane on top of that decision: it turns a RecoveryPlan into declared,
human-actionable/effect-bearing outcomes WITHOUT ever deciding policy itself.

    decide (recovery ladder datum) -> ACT (this engine) -> verify

The ladder is STILL the only decisioning (84.4 data-not-branches): this engine
consults `decide_recovery` and then materializes the declared action:
    RETRY      -> RetryContext with the injected failure snippet (never drops it)
    ROLLBACK   -> reset to `last_known_good` through the INJECTED git seam
    ESCALATE   -> EscalationBundle (package/step/attempts/evidence, creator-visible)
    HOLD       -> declared hold; nothing to effect
    RESTART/NONE -> declared as non-effect outcomes

Hermetic default (kickoff E / 84.4 precedent): the engine performs NO effects
on the SHIPPED default - the git seam is OPT-IN and never ambient. With no
seam injected, ROLLBACK is declared (target named) but not executed; with a
seam injected it emits the seam's byte datum. No clocks, no randomness, no
process calls, no model calls in this module.

Determinism (F-M2.3-6 / F-M2.4-6 fold-stability precedent, re-applied): same
state + same ledger + same attempts + same policy + same failure snippet ->
IDENTICAL RecoveryOutcome, always.

Additive law (M2.3-M2.5 / M3.2 / M3.3 precedent, re-applied): this module is
STRICTLY additive. Nothing below lives in a frozen module; no frozen module is
import-modified or touched. New task, new engine.
"""


from dataclasses import dataclass
from typing import Protocol

from jarvis.supervisor import (
    EvidenceLedger,
    LifecycleState,
    RecoveryAction,
    RecoveryPlan,
    RecoveryPolicy,
    decide_recovery,
)

from .mission_runner import MissionStep


class GitSeam(Protocol):
    """INJECTED git worktree adapter. Never ambient - supply it or accept
    declarations with no effect.

    live_worktree(): peek at the actual byte state the seam would mutate.
    rollback_to(commit): restore `commit` in the worktree; returns the byte
        datum (ok, message). The engine never calls git itself.
    """

    def live_worktree(self) -> str: ...

    def rollback_to(self, commit: str) -> tuple[bool, str]: ...


@dataclass(frozen=True)
class RetryContext:
    """The declared datum injected into a worker's fresh prompt on RETRY.

    `failure_snippet` is carried VERBATIM from the verifier datum (never
    summarized away): fresh failure bytes belong in the worker's next context.
    """

    step_id: str
    attempts_used: int
    failure_snippet: str
    prompt_suffix: str


@dataclass(frozen=True)
class EscalationBundle:
    """The creator-visible, human-actionable bundle for ESCALATE."""

    package: str
    step_id: str
    attempts_used: int
    reason: str
    current_worktree: str
    rollback_target: str | None
    failure_snippet: str


@dataclass(frozen=True)
class RecoveryOutcome:
    """The materialized ACT datum for exactly one declared ladder decision."""

    action: RecoveryAction
    step: MissionStep
    attempts_used: int
    reason: str
    retry: RetryContext | None = None
    escalation: EscalationBundle | None = None
    rolled_back_to: str | None = None
    rollback_ok: bool | None = None
    rollback_message: str = ""

    @property
    def effected(self) -> bool:
        """True when the outcome reached a real (seam-backed) effect."""
        return self.action is RecoveryAction.ROLLBACK and self.rollback_ok is not None


class RecoveryEngine:
    """The deterministic recovery ACT plane. Same datums -> same outcome."""

    __slots__ = ("_policy", "_git", "_package")

    def __init__(
        self,
        *,
        policy: RecoveryPolicy | None = None,
        git: GitSeam | None = None,
        package: str = "mission",
    ) -> None:
        self._policy = policy or RecoveryPolicy()
        self._git = git
        self._package = package

    @staticmethod
    def _prompt_suffix(step_id: str, attempts_used: int) -> str:
        return (
            f"[recovery] previous attempt #{attempts_used} for step {step_id} "
            f"failed; re-run the SAME task from the failure bytes below."
        )

    def act(
        self,
        *,
        step: MissionStep,
        state: LifecycleState,
        ledger: EvidenceLedger,
        attempts_used: int,
        failure_snippet: str,
        rollback_target: str | None,
    ) -> RecoveryOutcome:
        plan = decide_recovery(
            state=state,
            ledger=ledger,
            attempts_used=attempts_used,
            policy=self._policy,
            reason=f"step {step.id} failed; recovery ladder consulted",
        )
        base = RecoveryOutcome(
            action=plan.action,
            step=step,
            attempts_used=attempts_used,
            reason=plan.reason,
        )

        if plan.action in (RecoveryAction.RETRY, RecoveryAction.RESTART):
            return RecoveryOutcome(
                action=plan.action,
                step=step,
                attempts_used=attempts_used,
                reason=plan.reason,
                retry=RetryContext(
                    step_id=step.id,
                    attempts_used=attempts_used,
                    failure_snippet=failure_snippet,
                    prompt_suffix=self._prompt_suffix(step.id, attempts_used),
                ),
            )

        if plan.action is RecoveryAction.ROLLBACK:
            if self._git is not None and rollback_target is not None:
                ok, message = self._git.rollback_to(rollback_target)
                return RecoveryOutcome(
                    action=plan.action,
                    step=step,
                    attempts_used=attempts_used,
                    reason=plan.reason,
                    rolled_back_to=rollback_target,
                    rollback_ok=ok,
                    rollback_message=message,
                )
            return RecoveryOutcome(
                action=plan.action,
                step=step,
                attempts_used=attempts_used,
                reason=plan.reason + "; NO git seam injected - rollback DECLARED, not executed",
                rolled_back_to=rollback_target,
            )

        if plan.action is RecoveryAction.ESCALATE:
            return RecoveryOutcome(
                action=plan.action,
                step=step,
                attempts_used=attempts_used,
                reason=plan.reason,
                escalation=EscalationBundle(
                    package=self._package,
                    step_id=step.id,
                    attempts_used=attempts_used,
                    reason=plan.reason,
                    current_worktree=(
                        self._git.live_worktree() if self._git is not None else ""
                    ),
                    rollback_target=rollback_target,
                    failure_snippet=failure_snippet,
                ),
            )

        # HOLD / NONE: no effect, no bundle - the declared outcome is the datum.
        return base


__all__ = [
    "EscalationBundle",
    "GitSeam",
    "RecoveryEngine",
    "RecoveryOutcome",
    "RetryContext",
]