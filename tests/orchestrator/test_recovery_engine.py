from __future__ import annotations

"""M3.4 - the recovery ACT plane: ladder decision -> declared outcome
(84.4 determinism re-applied).

`RecoveryEngine.act` consumes the SAME frozen `decide_recovery` ladder datum
the supervisor uses, then materializes the declared action: RETRY/RESTART
carry the failure bytes into a `RetryContext` (never dropped), ROLLBACK
reaches the worktree ONLY through an injected GitSeam (hermetic default: no
seam -> declared, not executed), ESCALATE builds a creator-visible
`EscalationBundle`, HOLD/NONE declare nothing further. Same datums -> same
outcome, always. Hermetic: no I/O in this file.
"""

import pytest

from jarvis.orchestrator import (
    EscalationBundle,
    GitSeam,
    MissionStep,
    RecoveryEngine,
    RecoveryOutcome,
    RetryContext,
)
from jarvis.supervisor import (
    Evidence,
    EvidenceLedger,
    EvidenceSource,
    LifecycleState,
    RecoveryAction,
    RecoveryPlan,
    RecoveryPolicy,
)

ISO = "2026-09-21T00:00:00.000Z"


def _step(step_id: str, summary: str = "declared step") -> MissionStep:
    return MissionStep(id=step_id, summary=summary)


def _fresh_ledger() -> EvidenceLedger:
    return EvidenceLedger(
        observed_at=ISO,
        entries=(
            Evidence.declare(
                source=EvidenceSource.FILESYSTEM,
                summary="fresh: pytest exit 1 (assertion failed)",  # existing evidence
                observed_at=ISO,
            ),
        ),
    )


def _failing_ledger() -> EvidenceLedger:
    return EvidenceLedger(
        observed_at=ISO,
        entries=(
            Evidence.declare(
                source=EvidenceSource.FILESYSTEM,
                summary="fresh: worker retry evidence present",  # usable for RETRY
                observed_at=ISO,
            ),
        ),
    )


def test_exports_mirror_orchestrator_package() -> None:
    from jarvis import orchestrator

    for name in ("EscalationBundle", "GitSeam", "RecoveryEngine", "RecoveryOutcome", "RetryContext"):
        assert hasattr(orchestrator, name)


def test_retry_materializes_failure_bytes_verbatim() -> None:
    """RETRY datum -> a RetryContext that NEVER drops the failure snippet."""
    engine = RecoveryEngine(policy=RecoveryPolicy(max_attempts=3))
    outcome = engine.act(
        step=_step("s1"),
        state=LifecycleState.FAILED,
        ledger=_failing_ledger(),
        attempts_used=1,
        failure_snippet="AssertionError: value mismatch\nTraceback...",
        rollback_target="abc123",
    )
    assert outcome.action is RecoveryAction.RETRY
    assert outcome.retry is not None
    assert outcome.retry.step_id == "s1"
    assert outcome.retry.attempts_used == 1
    assert "AssertionError: value mismatch\nTraceback..." in outcome.retry.failure_snippet
    assert "re-run the SAME task" in outcome.retry.prompt_suffix
    assert outcome.effected is False


def test_restart_is_a_retry_context_without_execution() -> None:
    engine = RecoveryEngine()
    outcome = engine.act(
        step=_step("s1"),
        state=LifecycleState.FAILED,
        ledger=EvidenceLedger(observed_at=ISO),  # empty -> no fresh -> RESTART
        attempts_used=0,
        failure_snippet="no datum",
        rollback_target=None,
    )
    assert outcome.action is RecoveryAction.RESTART
    assert outcome.retry is not None
    assert outcome.rolled_back_to is None
    assert outcome.effected is False


def test_rollback_declared_without_seam_is_not_effected() -> None:
    """Hermetic default: ROLLBACK with NO git seam is DECLARED, not executed."""
    engine = RecoveryEngine(policy=RecoveryPolicy(max_attempts=1, rollback_available=True))
    outcome = engine.act(
        step=_step("s1"),
        state=LifecycleState.FAILED,
        ledger=_failing_ledger(),
        attempts_used=1,
        failure_snippet="boom",
        rollback_target="deadbeef",
    )
    assert outcome.action is RecoveryAction.ROLLBACK
    assert outcome.rolled_back_to == "deadbeef"
    assert outcome.rollback_ok is None
    assert outcome.effected is False
    assert "declared, not executed" in outcome.reason.lower()


class _FakeGit:
    """Injected seam: records the rollback target it would restore."""

    def __init__(self, ok: bool = True, worktree: str = "HEAD-CURRENT") -> None:
        self.ok = ok
        self.worktree = worktree
        self.calls: list[str] = []

    def live_worktree(self) -> str:
        return self.worktree

    def rollback_to(self, commit: str) -> tuple[bool, str]:
        self.calls.append(commit)
        if not self.ok:
            return False, f"rollback to {commit} failed"
        return True, f"restored {commit}"


def test_rollback_reaches_injected_git_seam() -> None:
    """With a seam injected, ROLLBACK emits the seam's byte datum."""
    git = _FakeGit(ok=True, worktree="worktree-aaaa")
    engine = RecoveryEngine(
        policy=RecoveryPolicy(max_attempts=1, rollback_available=True),
        git=git,
    )
    outcome = engine.act(
        step=_step("s1"),
        state=LifecycleState.FAILED,
        ledger=_failing_ledger(),
        attempts_used=1,
        failure_snippet="boom",
        rollback_target="deadbeef",
    )
    assert outcome.action is RecoveryAction.ROLLBACK
    assert outcome.rolled_back_to == "deadbeef"
    assert outcome.rollback_ok is True
    assert outcome.effected is True
    assert git.calls == ["deadbeef"]


def test_rollback_failure_is_reported_as_datum() -> None:
    git = _FakeGit(ok=False)
    engine = RecoveryEngine(
        policy=RecoveryPolicy(max_attempts=1, rollback_available=True),
        git=git,
    )
    outcome = engine.act(
        step=_step("s1"),
        state=LifecycleState.FAILED,
        ledger=_failing_ledger(),
        attempts_used=1,
        failure_snippet="boom",
        rollback_target="deadbeef",
    )
    assert outcome.rollback_ok is False
    assert outcome.effected is True  # it DID attempt the effect


def test_escalate_builds_creator_visible_bundle() -> None:
    git = _FakeGit(worktree="worktree-root")
    engine = RecoveryEngine(
        policy=RecoveryPolicy(max_attempts=1, escalate_after=1),
        git=git,
        package="M3.4",
    )
    outcome = engine.act(
        step=_step("s1"),
        state=LifecycleState.FAILED,
        ledger=_failing_ledger(),
        attempts_used=1,
        failure_snippet="secret stacktrace line",
        rollback_target="last-good",
    )
    assert outcome.action is RecoveryAction.ESCALATE
    assert outcome.escalation is not None
    bundle: EscalationBundle = outcome.escalation
    assert bundle.package == "M3.4"
    assert bundle.step_id == "s1"
    assert bundle.attempts_used == 1
    assert bundle.current_worktree == "worktree-root"
    assert bundle.rollback_target == "last-good"
    assert "secret stacktrace line" in bundle.failure_snippet


def test_hold_declares_no_effect_or_bundle() -> None:
    engine = RecoveryEngine(policy=RecoveryPolicy(max_attempts=1))
    outcome = engine.act(
        step=_step("s1"),
        state=LifecycleState.HELD,
        ledger=_fresh_ledger(),
        attempts_used=1,
        failure_snippet="stalled",
        rollback_target=None,
    )
    assert outcome.action is RecoveryAction.HOLD
    assert outcome.retry is None
    assert outcome.escalation is None
    assert outcome.rolled_back_to is None
    assert outcome.effected is False


def test_none_action_maps_to_base_outcome() -> None:
    engine = RecoveryEngine()
    outcome = engine.act(
        step=_step("s1"),
        state=LifecycleState.IMPLEMENTING,
        ledger=_fresh_ledger(),
        attempts_used=0,
        failure_snippet="not a failure",
        rollback_target=None,
    )
    assert outcome.action is RecoveryAction.NONE
    assert outcome.retry is None
    assert outcome.escalation is None


def test_act_is_a_deterministic_fold() -> None:
    """Same datums -> identical RecoveryOutcome, twice (F-M2.3-6 / F-M2.4-6)."""
    args = dict(
        step=_step("s1"),
        state=LifecycleState.FAILED,
        ledger=_failing_ledger(),
        attempts_used=1,
        failure_snippet="same bytes",
        rollback_target="abc",
    )
    engine = RecoveryEngine(policy=RecoveryPolicy(max_attempts=3))
    a = engine.act(**args)
    b = engine.act(**args)
    assert a == b
    assert a is not b
    assert a.action is b.action
    assert isinstance(a, RecoveryOutcome)


def test_ladder_decision_is_honored_not_redecided() -> None:
    """The engine never invents policy: it materializes the ladder's datum."""
    engine = RecoveryEngine(policy=RecoveryPolicy(max_attempts=3))
    outcome = engine.act(
        step=_step("s1"),
        state=LifecycleState.FAILED,
        ledger=_failing_ledger(),
        attempts_used=2,
        failure_snippet="bytes",
        rollback_target=None,
    )
    # attempts under max + fresh evidence -> the SAME symmetric RETRY the
    # ladder declares; engine did not substitute its own action.
    assert outcome.action is RecoveryAction.RETRY


def test_evidence_ledger_still_rules_freshness() -> None:
    """A ledger with only memory-level evidence cannot produce a RETRY: the
    ladder declares RESTART (no executable datum)."""
    engine = RecoveryEngine(policy=RecoveryPolicy(max_attempts=3))
    outcome = engine.act(
        step=_step("s1"),
        state=LifecycleState.FAILED,
        ledger=EvidenceLedger(
            observed_at=ISO,
            entries=(
                Evidence.declare(
                    source=EvidenceSource.AGENT_MEMORY,
                    summary="worker recollection only",
                    observed_at=ISO,
                ),
            ),
        ),
        attempts_used=0,
        failure_snippet="memory",
        rollback_target=None,
    )
    assert outcome.action is RecoveryAction.RESTART