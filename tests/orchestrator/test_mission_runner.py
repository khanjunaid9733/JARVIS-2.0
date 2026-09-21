from __future__ import annotations

"""M3.2 - the mission execution fold: declared plans ratchet step by step
(84.4 determinism re-applied).

`MissionRunner.run` is PURE DATA: same plan + same policy + same injected
verifier datum + same observed_at -> the SAME MissionRun, always. Each step
drives a FRESH TaskLifecycle to WORKER_VERIFY, and ONLY an injected
INDEPENDENT verifier (FILESYSTEM / FRESH_VERIFIER source) may move it to PASS
then FREEZE to FROZEN_SUCCESS. A worker claim (AGENT_MEMORY) can never set a
true value; a fail always returns to the declared RecoveryPolicy ladder,
bounded by max_attempts. The mission HALTS at the first step that cannot
reach FROZEN_SUCCESS in bounded repair. Hermetic: no I/O in this file.
"""

import pytest

from jarvis.orchestrator import (
    MissionPlan,
    MissionRun,
    MissionRunner,
    MissionStep,
)
from jarvis.supervisor import (
    EvidenceSource,
    LifecycleState,
    RecoveryAction,
    RecoveryPlan,
    RecoveryPolicy,
    VerificationResult,
)

ISO = "2026-09-21T00:00:00.000Z"


def _step(step_id: str, summary: str = "declared step") -> MissionStep:
    return MissionStep(id=step_id, summary=summary)


def _pass(result: bool, source: EvidenceSource) -> VerificationResult:
    return VerificationResult.decided(
        value=result,
        source=source,
        observed_at=ISO,
        summary="verifier seam datum",
    )


class _ScriptedVerifier:
    """Injected seam returning a fixed datum per step id (never the worker)."""

    def __init__(self, outcomes: dict[str, VerificationResult]) -> None:
        self.outcomes = outcomes
        self.calls: list[str] = []

    def verify(self, step: MissionStep) -> VerificationResult:
        self.calls.append(step.id)
        return self.outcomes[step.id]


class _RecordingDecomposer:
    def __init__(self, steps: tuple[MissionStep, ...]) -> None:
        self.steps = steps
        self.calls = 0

    def decompose(self, goal: str) -> tuple[MissionStep, ...]:
        self.calls += 1
        del goal
        return self.steps


def test_runner_exports_mirror_orchestrator_package() -> None:
    from jarvis import orchestrator

    for name in ("Decomposer", "MissionPlan", "MissionRun", "MissionRunner", "MissionStep", "MissionStepResult", "StepVerifier"):
        assert hasattr(orchestrator, name)


def test_declared_plan_preserves_order_and_defaults() -> None:
    plan = MissionPlan.declared("m", (_step("a"), _step("b")))
    assert plan.id == "m"
    assert [s.id for s in plan.steps] == ["a", "b"]
    assert len(plan) == 2
    assert plan.policy.max_attempts == 3


def test_all_steps_pass_reach_frozen_success() -> None:
    verifier = _ScriptedVerifier(
        {
            "a": _pass(True, EvidenceSource.FILESYSTEM),
            "b": _pass(True, EvidenceSource.FRESH_VERIFIER),
            "c": _pass(True, EvidenceSource.FILESYSTEM),
        }
    )
    plan = MissionPlan.declared("m", (_step("a"), _step("b"), _step("c")))
    run = MissionRunner().run(plan=plan, verifier=verifier, observed_at=ISO)

    assert run.accepted is True
    assert run.halted is False
    assert run.outcome == "ACCEPTED"
    assert [r.step.id for r in run.steps] == ["a", "b", "c"]
    assert all(r.final_state is LifecycleState.FROZEN_SUCCESS for r in run.steps)
    assert all(r.attempts_used == 1 for r in run.steps)
    assert verifier.calls == ["a", "b", "c"]


def test_only_executable_sources_may_move_the_ratchet() -> None:
    """A worker claim (AGENT_MEMORY) is NEVER a true value: it cannot pass."""
    verifier = _ScriptedVerifier({"a": _pass(True, EvidenceSource.AGENT_MEMORY)})
    plan = MissionPlan.declared("m", (_step("a"),))
    run = MissionRunner().run(plan=plan, verifier=verifier, observed_at=ISO)

    assert run.accepted is False
    assert run.outcome == "HELD"


def test_failure_then_fresh_pass_uses_retry_within_policy() -> None:
    """FILESYSTEM fail datum + attempts below max -> RETRY -> FROZEN_SUCCESS."""
    base = _ScriptedVerifier(
        {
            "a": _pass(True, EvidenceSource.FILESYSTEM),
            "b": _pass(True, EvidenceSource.FILESYSTEM),
        }
    )
    state = {"b_seen": 0}

    class _FlakyOnce:
        def verify(self, step: MissionStep) -> VerificationResult:
            if step.id == "b":
                state["b_seen"] += 1
                if state["b_seen"] == 1:
                    return _pass(False, EvidenceSource.FILESYSTEM)
            return base.verify(step)

    plan = MissionPlan.declared("m", (_step("a"), _step("b")))
    run = MissionRunner().run(
        plan=plan,
        verifier=_FlakyOnce(),
        observed_at=ISO,
    )

    assert run.accepted is True
    step_b = run.steps[1]
    assert step_b.attempts_used == 2
    assert step_b.final_state is LifecycleState.FROZEN_SUCCESS


def test_exhaustion_without_rollback_halts_held() -> None:
    """max_attempts reached + no rollback datum -> HOLD (L2 creator gate)."""
    verifier = _ScriptedVerifier({"a": _pass(False, EvidenceSource.FILESYSTEM)})
    plan = MissionPlan(
        id="m",
        steps=(_step("a"), _step("b")),
        policy=RecoveryPolicy(max_attempts=2, rollback_available=False),
    )
    run = MissionRunner().run(plan=plan, verifier=verifier, observed_at=ISO)

    assert run.accepted is False
    assert run.outcome == "HELD"
    step_a = run.last
    assert step_a is not None
    assert step_a.attempts_used == 2
    assert step_a.final_state is LifecycleState.HELD
    assert step_a.recovery is not None
    assert step_a.recovery.action is RecoveryAction.HOLD
    assert step_a.recovery.creator_gated is True
    # Mission halts: step "b" never ran.
    assert len(run.steps) == 1
    assert verifier.calls == ["a", "a"]


def test_exhaustion_with_rollback_halts_rolled_back() -> None:
    verifier = _ScriptedVerifier({"a": _pass(False, EvidenceSource.FILESYSTEM)})
    plan = MissionPlan(
        id="m",
        steps=(_step("a"),),
        policy=RecoveryPolicy(max_attempts=1, rollback_available=True),
    )
    run = MissionRunner().run(plan=plan, verifier=verifier, observed_at=ISO)

    assert run.outcome == "ROLLED_BACK"
    step_a = run.last
    assert step_a is not None
    assert step_a.final_state is LifecycleState.FAILED
    assert step_a.recovery is not None
    assert step_a.recovery.action is RecoveryAction.ROLLBACK


def test_escalate_after_bound_moves_to_escalated() -> None:
    verifier = _ScriptedVerifier({"a": _pass(False, EvidenceSource.FILESYSTEM)})
    plan = MissionPlan(
        id="m",
        steps=(_step("a"),),
        policy=RecoveryPolicy(max_attempts=2, rollback_available=True, escalate_after=2),
    )
    run = MissionRunner().run(plan=plan, verifier=verifier, observed_at=ISO)

    assert run.accepted is False
    assert run.outcome == "ESCALATED"
    step_a = run.last
    assert step_a is not None
    assert step_a.final_state is LifecycleState.ESCALATED
    assert step_a.recovery is not None
    assert step_a.recovery.action is RecoveryAction.ESCALATE


def test_no_fresh_evidence_restarts_from_clean_context() -> None:
    """Fresh but non-executable datum (FRESH_VERIFIER fail) -> RESTART, and a
    clean-context rerun that passes reaches FROZEN_SUCCESS."""
    attempts = {"calls": 0}

    class _RestartOnce:
        def verify(self, step: MissionStep) -> VerificationResult:
            attempts["calls"] += 1
            if attempts["calls"] == 1:
                return _pass(False, EvidenceSource.FRESH_VERIFIER)
            return _pass(True, EvidenceSource.FILESYSTEM)

    plan = MissionPlan(
        id="m",
        steps=(_step("a"),),
        policy=RecoveryPolicy(max_attempts=3, rollback_available=True),
    )
    run = MissionRunner().run(
        plan=plan,
        verifier=_RestartOnce(),
        observed_at=ISO,
    )

    assert run.accepted is True
    assert run.last is not None
    assert run.last.attempts_used == 2
    assert run.last.final_state is LifecycleState.FROZEN_SUCCESS


def test_mission_halts_at_first_non_accepted_step() -> None:
    verifier = _ScriptedVerifier(
        {
            "a": _pass(True, EvidenceSource.FILESYSTEM),
            "b": _pass(False, EvidenceSource.FILESYSTEM),  # exhausts on 1 attempt
            "c": _pass(True, EvidenceSource.FILESYSTEM),
        }
    )
    plan = MissionPlan(
        id="m",
        steps=(_step("a"), _step("b"), _step("c")),
        policy=RecoveryPolicy(max_attempts=1, rollback_available=False),
    )
    run = MissionRunner().run(plan=plan, verifier=verifier, observed_at=ISO)

    assert [r.step.id for r in run.steps] == ["a", "b"]
    assert run.accepted is False
    assert run.outcome == "HELD"
    assert verifier.calls == ["a", "b"]


def test_run_is_a_deterministic_fold() -> None:
    """Same datums -> identical MissionRun, twice (F-M2.3-6 / F-M2.4-6)."""
    plan = MissionPlan.declared("m", (_step("a"), _step("b")))
    verifier = _ScriptedVerifier(
        {
            "a": _pass(True, EvidenceSource.FILESYSTEM),
            "b": _pass(True, EvidenceSource.FRESH_VERIFIER),
        }
    )
    runner = MissionRunner()
    r1 = runner.run(plan=plan, verifier=verifier, observed_at=ISO)
    r2 = runner.run(plan=plan, verifier=verifier, observed_at=ISO)
    assert r1 == r2
    assert r1 is not r2
    assert r1.accepted == r2.accepted


def test_decompose_and_run_is_opt_in_proposal_plane() -> None:
    decomposer = _RecordingDecomposer((_step("a"), _step("b")))
    verifier = _ScriptedVerifier(
        {
            "a": _pass(True, EvidenceSource.FILESYSTEM),
            "b": _pass(True, EvidenceSource.FILESYSTEM),
        }
    )
    run = MissionRunner().decompose_and_run(
        goal="g",
        decomposer=decomposer,
        verifier=verifier,
        observed_at=ISO,
    )
    assert decomposer.calls == 1
    assert run.accepted is True
    assert [r.step.id for r in run.steps] == ["a", "b"]


def test_empty_plan_accepts_vacuously() -> None:
    plan = MissionPlan.declared("m", tuple())
    run = MissionRunner().run(
        plan=plan,
        verifier=_ScriptedVerifier({}),
        observed_at=ISO,
    )
    assert run.accepted is True
    assert run.outcome == "ACCEPTED"
    assert run.steps == tuple()


def test_accepted_is_outcome_defined_vacuous_inclusive() -> None:
    assert MissionRun(plan_id="m", steps=tuple(), outcome="ACCEPTED").accepted is True
    assert MissionRun(plan_id="m", steps=tuple(), outcome="HELD").accepted is False
    assert MissionRun(plan_id="m", steps=tuple(), outcome="HELD").halted is True


def test_recovery_plan_datum_is_a_decided_dataclass() -> None:
    plan = RecoveryPlan(
        action=RecoveryAction.HOLD,
        reason="exhausted",
        attempts_used=3,
        creator_gated=True,
    )
    assert isinstance(plan, RecoveryPlan)
    assert plan.action is RecoveryAction.HOLD


def test_runner_never_mutates_frozen_inputs() -> None:
    """The fold is additive: declared plans and verifier datums are unchanged."""
    plan = MissionPlan.declared("m", (_step("a"),))
    verifier = _ScriptedVerifier({"a": _pass(True, EvidenceSource.FILESYSTEM)})
    plan_before = plan
    result = MissionRunner().run(plan=plan, verifier=verifier, observed_at=ISO)
    assert result.accepted is True
    assert plan == plan_before
    assert plan.steps == plan_before.steps