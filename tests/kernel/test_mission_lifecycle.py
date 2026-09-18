from __future__ import annotations

"""Module 14 deterministic mission-lifecycle FSM tests (STRETCH M1.1, §134.1).

All tests are synchronous except the F-E15 observer-span test, which needs
an `anyio`-marked async adapter run.  Every effect.* event stamped in these
tests carries an explicit `mission_id` matching the test's lifecycle —
documented M1.1 boundary (M2 orchestrator tags them in production; the
kernel envelope engine does not set mission_id).
"""

import pytest

from jarvis.kernel.done_gate import CompletionGate
from jarvis.kernel.effect_envelope import EffectEnvelopeEngine
from jarvis.kernel.event_log import Event, EventLog, new_ulid
from jarvis.kernel.intent import Budget, Manifest, ResolvedContract
from jarvis.kernel.mission_lifecycle import (
    EFFECT_FAILED,
    EFFECT_REFUSED,
    LIFECYCLE_ACCEPTED,
    LIFECYCLE_COMPLETED,
    LIFECYCLE_COMPENSATED,
    LIFECYCLE_REFUSED,
    MISSION_STARTED,
    MISSION_STREAM_ID,
    TRANSITIONS,
    LIFECYCLE_EVENT_BY_STATE,
    TERMINAL_STATES,
    MissionLifecycle,
    MissionLifecycleOwner,
)
from jarvis.kernel.registry import CapabilityRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FixedClock:
    def __init__(self, ts: str) -> None:
        self._ts = ts
    def now_utc_iso(self) -> str:
        return self._ts


def _log(tmp_path, name: str = "log.db", clock_ts: str = "2026-09-18T00:00:00.000Z", observer=None) -> EventLog:
    return EventLog(db_path=str(tmp_path / name), clock=_FixedClock(clock_ts), observer=observer)


def _append_event(
    log: EventLog,
    *,
    event_type: str,
    mission_id: str,
    principal: str = "model.agent",
    stream_id: str = "mission",
    payload: dict | None = None,
    task_id: str | None = None,
    cause: str | None = None,
    event_id: str | None = None,
) -> str:
    return log.append(
        Event(
            event_id=event_id,
            stream_id=stream_id,
            event_type=event_type,
            principal_id=principal,
            mission_id=mission_id,
            task_id=task_id,
            cause_event_id=cause,
            correlation_id=mission_id,
            payload=dict(payload or {}),
        )
    )


class _SpyAdapter:
    def __init__(self, provider_id: str, result: dict | None = None) -> None:
        self._provider_id = provider_id
        self.result = {"ok": True} if result is None else result
        self.calls = 0

    @property
    def provider_id(self) -> str:
        return self._provider_id

    async def invoke(self, contract_id: str, version: str, args: dict) -> dict:
        self.calls += 1
        return self.result

    def health_check(self) -> bool:
        return True


def _manifest() -> Manifest:
    return Manifest(
        manifest_id="m14-manifest",
        intent_id="intent-14",
        contracts=[
            ResolvedContract(id="fs.read", version="1.0.0", args={})
        ],
        required_capabilities=["fs.read"],
        budget=Budget(),
        constraints={},
        risk_class="safe",
        manifest_sha256="0" * 64,
        created_at_utc="2026-09-18T00:00:00Z",
    )


# ---------------------------------------------------------------------------
# Data table invariants
# ---------------------------------------------------------------------------

def test_transition_table_and_lifecycle_coverage_are_data():
    all_targets = set(TRANSITIONS.values())
    assert all_targets == set(LIFECYCLE_EVENT_BY_STATE.keys())
    assert all_targets <= {"pending", "executing", "completed", "refused", "compensated"}
    # no transitions out of terminal states (belt-and-suspenders with absorbing guard)
    for target in TERMINAL_STATES:
        assert not any(k[0] == target for k in TRANSITIONS)


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

def test_initial_lifecycle_is_pending(tmp_path):
    log = _log(tmp_path)
    state = MissionLifecycleOwner(log, mission_id="m1").rebuild()
    assert state.state == "pending"
    assert state.event_count == 0
    assert state.effects == ()
    assert state.compensation == ()
    assert state.is_terminal() is False


# ---------------------------------------------------------------------------
# mission.started -> executing (lifecycle.accepted)
# ---------------------------------------------------------------------------

def test_mission_started_transitions_to_executing(tmp_path):
    log = _log(tmp_path)
    mid = "m-start"

    started_id = _append_event(log, event_type=MISSION_STARTED, mission_id=mid)
    owner = MissionLifecycleOwner(log, mission_id=mid)

    state, appended = owner.advance()

    assert state.state == "executing"
    assert state.event_count == 1
    assert len(appended) == 1

    lifecycle_events = [e for e in log.replay() if e.event_type.startswith("lifecycle.")]
    assert len(lifecycle_events) == 1
    le = lifecycle_events[0]
    assert le.stream_id == MISSION_STREAM_ID
    assert le.principal_id == "model.agent"
    assert le.mission_id == mid
    assert le.cause_event_id == started_id
    assert le.correlation_id == mid
    assert le.payload["from"] == "pending"
    assert le.payload["to"] == "executing"
    assert le.payload["intake_event_type"] == MISSION_STARTED
    assert le.payload["cause_event_id"] == started_id


# ---------------------------------------------------------------------------
# task.completed -> completed (lifecycle.completed)
# ---------------------------------------------------------------------------

def test_full_success_to_completed(tmp_path):
    log = _log(tmp_path)
    mid = "m-full"

    _append_event(log, event_type=MISSION_STARTED, mission_id=mid)
    _append_event(
        log,
        event_type="task.completed",
        mission_id=mid,
        stream_id="orchestration",
        task_id="t1",
        payload={"kind": "task.completion", "passed": True, "checks": [], "evidence": {}},
    )
    state, appended = MissionLifecycleOwner(log, mission_id=mid).advance()

    assert state.state == "completed"
    assert state.is_terminal() is True
    assert len(appended) == 2  # lifecycle.accepted + lifecycle.completed
    assert log.verify_chain() is True


# ---------------------------------------------------------------------------
# task.completion_refused -> refused (lifecycle.refused)
# ---------------------------------------------------------------------------

def test_completion_refused_transitions_to_refused(tmp_path):
    log = _log(tmp_path)
    mid = "m-refuse"

    _append_event(log, event_type=MISSION_STARTED, mission_id=mid)
    _append_event(
        log,
        event_type="task.completion_refused",
        mission_id=mid,
        stream_id="orchestration",
        task_id="t1",
        payload={"kind": "task.completion", "passed": False, "checks": [], "evidence": {}},
    )
    state, appended = MissionLifecycleOwner(log, mission_id=mid).advance()

    assert state.state == "refused"
    assert state.is_terminal() is True
    assert len(appended) == 2


# ---------------------------------------------------------------------------
# effect.failed -> compensated (both from pending and executing)
# ---------------------------------------------------------------------------

def test_effect_failed_from_executing_compensates(tmp_path):
    log = _log(tmp_path)
    mid = "m-comp"

    _append_event(log, event_type=MISSION_STARTED, mission_id=mid)
    eid = _append_event(
        log,
        event_type=EFFECT_FAILED,
        mission_id=mid,
        payload={"effect_id": "e-f1", "intended_change": {"file": "a.txt"}},
    )
    state, appended = MissionLifecycleOwner(log, mission_id=mid).advance()

    assert state.state == "compensated"
    assert state.is_terminal() is True
    assert len(state.compensation) == 1
    comp = state.compensation[0]
    assert comp.effect_id == "e-f1"
    assert comp.failed_event_id == eid
    assert comp.intended_change == {"file": "a.txt"}
    assert comp.status == "declared"
    assert len(appended) == 2  # lifecycle.accepted + lifecycle.compensated
    assert log.verify_chain() is True


def test_effect_failed_before_mission_started_compensates_from_pending(tmp_path):
    log = _log(tmp_path)
    mid = "m-early-fail"

    _append_event(
        log,
        event_type=EFFECT_FAILED,
        mission_id=mid,
        payload={"effect_id": "e-f0", "intended_change": {"early": True}},
    )
    state, appended = MissionLifecycleOwner(log, mission_id=mid).advance()

    assert state.state == "compensated"
    assert len(state.compensation) == 1
    assert state.compensation[0].effect_id == "e-f0"
    assert len(appended) == 1  # lifecycle.compensated only


# ---------------------------------------------------------------------------
# effect.refused folds but does NOT terminate the mission
# ---------------------------------------------------------------------------

def test_effect_refused_folds_without_terminating(tmp_path):
    log = _log(tmp_path)
    mid = "m-ref"

    _append_event(
        log,
        event_type=EFFECT_REFUSED,
        mission_id=mid,
        payload={"effect_id": "e-r1", "intended_change": {"gone": True}},
    )
    _append_event(log, event_type=MISSION_STARTED, mission_id=mid)
    _append_event(
        log,
        event_type="task.completed",
        mission_id=mid,
        stream_id="orchestration",
        task_id="t2",
        payload={"kind": "task.completion", "passed": True, "checks": [], "evidence": {}},
    )
    state, appended = MissionLifecycleOwner(log, mission_id=mid).advance()

    assert state.state == "completed"  # reached completed despite earlier refusal
    assert len(state.effects) == 1
    assert state.effects[0].effect_id == "e-r1"
    assert state.effects[0].phase == EFFECT_REFUSED


# ---------------------------------------------------------------------------
# Terminal absorbing: later events are fully ignored
# ---------------------------------------------------------------------------

def test_terminal_absorbs_later_events(tmp_path):
    log = _log(tmp_path)
    mid = "m-absorb"

    _append_event(log, event_type=MISSION_STARTED, mission_id=mid)
    _append_event(
        log,
        event_type="task.completed",
        mission_id=mid,
        stream_id="orchestration",
        task_id="t1",
        payload={"kind": "task.completion", "passed": True, "checks": [], "evidence": {}},
    )
    _append_event(
        log,
        event_type=EFFECT_FAILED,
        mission_id=mid,
        payload={"effect_id": "e-late", "intended_change": {}},
    )
    _append_event(
        log,
        event_type="task.completion_refused",
        mission_id=mid,
        stream_id="orchestration",
        task_id="t2",
        payload={"kind": "task.completion", "passed": False, "checks": [], "evidence": {}},
    )
    state, appended = MissionLifecycleOwner(log, mission_id=mid).advance()

    assert state.state == "completed"
    assert state.event_count == 2  # only the two intake events before terminal
    assert len(state.effects) == 0  # absorbed, not folded
    assert len(state.compensation) == 0
    assert len(appended) == 2  # no new lifecycle events


# ---------------------------------------------------------------------------
# Idempotent advance + loop-safety (no lifecycle.* re-triggered)
# ---------------------------------------------------------------------------

def test_advance_is_idempotent_no_loop(tmp_path):
    log = _log(tmp_path)
    mid = "m-idem"

    _append_event(log, event_type=MISSION_STARTED, mission_id=mid)
    _append_event(
        log,
        event_type="task.completed",
        mission_id=mid,
        stream_id="orchestration",
        task_id="t1",
        payload={"kind": "task.completion", "passed": True, "checks": [], "evidence": {}},
    )
    owner = MissionLifecycleOwner(log, mission_id=mid)

    state1, appended1 = owner.advance()
    state2, appended2 = owner.advance()

    assert state1.state == state2.state == "completed"
    assert state1.digest() == state2.digest()
    assert appended2 == []  # nothing appended on second advance
    assert log.verify_chain() is True

    lifecycle_events = [e for e in log.replay() if e.event_type.startswith("lifecycle.")]
    assert len(lifecycle_events) == 2  # exactly lifecycle.accepted + lifecycle.completed


# ---------------------------------------------------------------------------
# Rebuild determinism: rebuild twice → identical state and digest
# ---------------------------------------------------------------------------

def test_rebuild_is_pure_digest_stable(tmp_path):
    log = _log(tmp_path)
    mid = "m-pure"

    _append_event(log, event_type=MISSION_STARTED, mission_id=mid)
    _append_event(
        log,
        event_type="task.completed",
        mission_id=mid,
        stream_id="orchestration",
        task_id="t1",
        payload={"kind": "task.completion", "passed": True, "checks": [], "evidence": {}},
    )
    MissionLifecycleOwner(log, mission_id=mid).advance()

    r1 = MissionLifecycleOwner(log, mission_id=mid).rebuild()
    r2 = MissionLifecycleOwner(log, mission_id=mid).rebuild()

    assert r1 == r2
    assert r1.digest() == r2.digest()


# ---------------------------------------------------------------------------
# Digest changes when log content differs
# ---------------------------------------------------------------------------

def test_digest_differs_for_different_logs(tmp_path):
    log_a = _log(tmp_path, name="a.db")
    log_b = _log(tmp_path, name="b.db")
    mid = "m-diff"

    _append_event(log_a, event_type=MISSION_STARTED, mission_id=mid)
    _append_event(
        log_b,
        event_type=EFFECT_FAILED,
        mission_id=mid,
        payload={"effect_id": "e-x", "intended_change": {}},
    )

    digest_a = MissionLifecycleOwner(log_a, mission_id=mid).rebuild().digest()
    digest_b = MissionLifecycleOwner(log_b, mission_id=mid).rebuild().digest()

    assert digest_a != digest_b


# ---------------------------------------------------------------------------
# NAT-03: digest is clock-independent for identical SEMANTIC logs. Event
# ULIDs are part of the hashed state (`failed_event_id`, like memories keyed
# by event id in module 7), so identical logs are defined by identical event
# ids — feed fixed ids to isolate the clock variable.
# ---------------------------------------------------------------------------

def test_digest_excludes_wall_clock_timestamps(tmp_path):
    # log content is identical except the wall clock:
    # timestamps (ts_utc) live on events, never in folded state.
    def build(name: str, clock_ts: str) -> tuple[str, str]:
        log = _log(tmp_path, name=name, clock_ts=clock_ts)
        mid = "m-clock"
        _append_event(
            log,
            event_type=MISSION_STARTED,
            mission_id=mid,
            event_id="fixed-start",
        )
        _append_event(
            log,
            event_type=EFFECT_FAILED,
            mission_id=mid,
            payload={"effect_id": "e-same", "intended_change": {"file": "x"}},
            event_id="fixed-fail",
        )
        MissionLifecycleOwner(log, mission_id=mid).advance()
        state = MissionLifecycleOwner(log, mission_id=mid).rebuild()
        return state.state, state.digest()

    state_jan, digest_jan = build("clock-1.db", "2026-01-01T00:00:00.000Z")
    state_dec, digest_dec = build("clock-2.db", "2026-12-31T23:59:59.999Z")

    assert (state_jan, state_dec) == ("compensated", "compensated")
    assert digest_jan == digest_dec  # identical digests across different clocks


# ---------------------------------------------------------------------------
# Mission isolation: events for other missions are ignored
# ---------------------------------------------------------------------------

def test_mission_isolation(tmp_path):
    log = _log(tmp_path)

    _append_event(log, event_type=MISSION_STARTED, mission_id="m-self")
    _append_event(log, event_type=MISSION_STARTED, mission_id="m-other")
    _append_event(
        log,
        event_type="task.completed",
        mission_id="m-other",
        stream_id="orchestration",
        task_id="t-other",
        payload={"kind": "task.completion", "passed": True, "checks": [], "evidence": {}},
    )

    state_self, _ = MissionLifecycleOwner(log, mission_id="m-self").advance()
    state_other, _ = MissionLifecycleOwner(log, mission_id="m-other").advance()

    assert state_self.state == "executing"  # only mission.started folded
    assert state_other.state == "completed"  # mission.started + task.completed


# ---------------------------------------------------------------------------
# NAT-05: owner never appends task.completed — only CompletionGate does
# ---------------------------------------------------------------------------

def test_nat05_owner_never_appends_task_completed(tmp_path):
    log = _log(tmp_path)
    mid = "m-nat05"

    _append_event(log, event_type=MISSION_STARTED, mission_id=mid)

    gate = CompletionGate(log, principal_id="model.agent")
    gate.declare_completion(
        task_id="t1",
        mission_id=mid,
        evidence={"artifact": "plan.md", "verification": "tests passed"},
    )

    state, appended = MissionLifecycleOwner(log, mission_id=mid).advance()

    all_events = log.replay()
    task_completed = [e for e in all_events if e.event_type == "task.completed"]
    lifecycle_completed = [e for e in all_events if e.event_type == LIFECYCLE_COMPLETED]

    assert len(task_completed) == 1
    assert task_completed[0].mission_id == mid
    assert len(lifecycle_completed) == 1
    assert state.state == "completed"
    assert log.verify_chain() is True


# ---------------------------------------------------------------------------
# Causal discipline: lifecycle events carry cause_event_id + correlation_id
# ---------------------------------------------------------------------------

def test_causal_discipline_on_all_lifecycle_types(tmp_path):
    mid = "m-causal"

    cases = [
        ("pending", MISSION_STARTED, "executing", LIFECYCLE_ACCEPTED),
        ("executing", "task.completed", "completed", LIFECYCLE_COMPLETED),
        ("executing", "task.completion_refused", "refused", LIFECYCLE_REFUSED),
        ("executing", EFFECT_FAILED, "compensated", LIFECYCLE_COMPENSATED),
        ("pending", EFFECT_FAILED, "compensated", LIFECYCLE_COMPENSATED),
    ]

    for i, (initial, intake_type, target_state, expected_lifecycle) in enumerate(cases):
        log = _log(tmp_path, name=f"causal-{i}-{target_state}.db")
        owner = MissionLifecycleOwner(log, mission_id=mid)

        if initial == "executing":
            # prime the mission into executing BEFORE the intake event
            _append_event(log, event_type=MISSION_STARTED, mission_id=mid)
            primed, _ = owner.advance()
            assert primed.state == "executing"

        intake_id = _append_event(log, event_type=intake_type, mission_id=mid)
        state, _ = owner.advance()

        assert state.state == target_state
        lifecycle = [e for e in log.replay() if e.event_type == expected_lifecycle]
        assert len(lifecycle) == 1
        assert lifecycle[0].cause_event_id == intake_id
        assert lifecycle[0].correlation_id == mid
        assert lifecycle[0].stream_id == MISSION_STREAM_ID


# ---------------------------------------------------------------------------
# Fold consistency: digest after stepwise advance == digest after full rebuild
# ---------------------------------------------------------------------------

def test_advance_digest_matches_full_rebuild_digest(tmp_path):
    log = _log(tmp_path)
    mid = "m-fold-agree"
    owner = MissionLifecycleOwner(log, mission_id=mid)

    _append_event(log, event_type=MISSION_STARTED, mission_id=mid)
    state_step1, _ = owner.advance()
    assert state_step1.state == "executing"
    digest_step1 = state_step1.digest()

    _append_event(
        log,
        event_type=EFFECT_FAILED,
        mission_id=mid,
        payload={"effect_id": "e-agree", "intended_change": {"stable": True}},
    )
    state_step2, _ = owner.advance()
    assert state_step2.state == "compensated"

    # Folding in two steps, then folding the same log at once, gives the same
    # state AND the same digest (the fold is a pure function of the log).
    state_full = owner.rebuild()
    assert state_full == state_step2
    assert state_full.digest() == state_step2.digest()

    # event_count counts the intake events folded from the log, regardless
    # of how the fold was reached (2 = mission.started + effect.failed).
    assert state_full.event_count == 2


# ---------------------------------------------------------------------------
# effect_id tracking is latest-phase per effect_id
# ---------------------------------------------------------------------------

def test_effect_record_tracks_latest_phase(tmp_path):
    log = _log(tmp_path)
    mid = "m-phases"

    for phase in ["effect.prepared", "effect.authorized", "effect.committed", "effect.verified"]:
        _append_event(log, event_type=phase, mission_id=mid, payload={"effect_id": "e-seq"})

    state = MissionLifecycleOwner(log, mission_id=mid).rebuild()

    assert len(state.effects) == 1
    assert state.effects[0].effect_id == "e-seq"
    assert state.effects[0].phase == "effect.verified"  # latest phase


# ---------------------------------------------------------------------------
# Post-review reconciliation (Antigravity pass, F-M14 findings):
#   F-M14-1  engine-built effects must fold into the mission (seam closed)
#   F-M14-2  multi-effect missions record EVERY failure in the ledger
#   F-M14-3  completion/refusal must not strand a pending mission
#   F-M14-4  malformed intended_change must not crash replay
#   F-M14-5  non-effect events must not corrupt the effect ledger
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_f14_1_engine_built_effects_fold_into_lifecycle(tmp_path):
    log = _log(tmp_path)
    mid = "m-seam"
    owner = MissionLifecycleOwner(log, mission_id=mid)
    registry = CapabilityRegistry.seed_m1_defaults()
    adapters = {"fs.default": _SpyAdapter("fs.default")}

    _append_event(log, event_type=MISSION_STARTED, mission_id=mid)

    engine = owner.build_effect_engine(registry, adapters)
    verified = await engine.run(
        _manifest(),
        "fs.read",
        intended_change={"path": "/tmp/ok"},
        postconditions={"ok": True},
        idempotency_key="k-seam-ok",
    )

    from jarvis.kernel.effect_envelope import EffectEnvelope
    assert isinstance(verified, EffectEnvelope)

    state = owner.rebuild()
    assert state.state == "executing"  # verified effects do not terminate
    assert len(state.effects) == 1
    assert state.effects[0].phase == "effect.verified"

    # A second, UNVERIFIED effect now drives the mission to compensated and
    # lands a compensation record — engine-emitted effect.failed is visible.
    adapters["fs.default"].result = {"ok": False}
    failed = await engine.run(
        _manifest(),
        "fs.read",
        intended_change={"path": "/tmp/fail"},
        postconditions={"ok": True},
        idempotency_key="k-seam-fail",
    )
    from jarvis.kernel.effect_envelope import EffectFailure
    assert isinstance(failed, EffectFailure)

    state2 = owner.rebuild()
    assert state2.state == "compensated"
    assert len(state2.compensation) == 1
    assert state2.compensation[0].effect_id is not None
    assert log.verify_chain() is True


def test_f14_2_every_failed_effect_is_recorded_for_compensation(tmp_path):
    log = _log(tmp_path)
    mid = "m-multi-fail"

    _append_event(log, event_type=MISSION_STARTED, mission_id=mid)
    _append_event(
        log,
        event_type=EFFECT_FAILED,
        mission_id=mid,
        payload={"effect_id": "effect-1", "intended_change": {"action": "write-1"}},
    )
    _append_event(
        log,
        event_type=EFFECT_FAILED,
        mission_id=mid,
        payload={"effect_id": "effect-2", "intended_change": {"action": "write-2"}},
    )

    state = MissionLifecycleOwner(log, mission_id=mid).rebuild()

    assert state.state == "compensated"
    assert len(state.compensation) == 2  # both failures registered (§83)
    assert [c.effect_id for c in state.compensation] == ["effect-1", "effect-2"]
    assert len(state.effects) == 2  # one latest-phase record per effect_id
    assert {r.phase for r in state.effects} == {EFFECT_FAILED}


def test_f14_3_completion_from_pending_is_not_a_zombie(tmp_path):
    log = _log(tmp_path)
    mid = "m-zombie"

    _append_event(
        log,
        event_type="task.completed",
        mission_id=mid,
        stream_id="orchestration",
        task_id="t1",
        payload={"kind": "task.completion", "passed": True, "checks": [], "evidence": {}},
    )
    state, appended = MissionLifecycleOwner(log, mission_id=mid).advance()

    assert state.state == "completed"
    assert state.is_terminal() is True
    assert len(appended) == 1  # exactly lifecycle.completed emitted
    lifecycle_types = [
        e.event_type for e in log.replay() if e.event_type.startswith("lifecycle.")
    ]
    assert lifecycle_types == [LIFECYCLE_COMPLETED]

    log2 = _log(tmp_path, name="zombie-refused.db")
    _append_event(
        log2,
        event_type="task.completion_refused",
        mission_id=mid,
        stream_id="orchestration",
        task_id="t2",
        payload={"kind": "task.completion", "passed": False, "checks": [], "evidence": {}},
    )
    state2, appended2 = MissionLifecycleOwner(log2, mission_id=mid).advance()

    assert state2.state == "refused"
    assert len(appended2) == 1  # lifecycle.refused emitted


def test_f14_4_malformed_intended_change_does_not_crash_replay(tmp_path):
    log = _log(tmp_path)
    mid = "m-poison"

    _append_event(log, event_type=MISSION_STARTED, mission_id=mid)
    _append_event(
        log,
        event_type=EFFECT_FAILED,
        mission_id=mid,
        payload={"effect_id": "e-bad", "intended_change": "string-not-dict"},
    )

    state = MissionLifecycleOwner(log, mission_id=mid).rebuild()

    assert state.state == "compensated"
    assert len(state.compensation) == 1
    # non-dict intended_change is preserved verbatim under a raw key, never
    # coerced by dict(...) in a way that can raise during fold.
    assert state.compensation[0].intended_change == {"raw": "string-not-dict"}
    assert log.verify_chain() is True


def test_f14_5_non_effect_event_does_not_corrupt_effect_ledger(tmp_path):
    log = _log(tmp_path)
    mid = "m-ledger"

    _append_event(log, event_type=MISSION_STARTED, mission_id=mid)
    _append_event(
        log,
        event_type="task.completed",
        mission_id=mid,
        stream_id="orchestration",
        task_id="t1",
        payload={"effect_id": "not-an-effect", "kind": "task.completion",
                 "passed": True, "checks": [], "evidence": {}},
    )

    state = MissionLifecycleOwner(log, mission_id=mid).rebuild()

    assert state.state == "completed"
    assert state.effects == ()  # task.completed cannot join the effect ledger


# ---------------------------------------------------------------------------
# F-E15: build_effect_engine threads observer into every built engine
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_f_e15_build_effect_engine_threads_observer(tmp_path):
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from jarvis.observability import (
        SPAN_EVENT,
        configure_otel,
        effect_span_name,
        verify_span_name,
    )

    exporter = InMemorySpanExporter()
    observer = configure_otel(exporter=exporter)
    log = _log(tmp_path, observer=observer)
    mid = "m-f-e15"

    registry = CapabilityRegistry.seed_m1_defaults()
    adapters = {"fs.default": _SpyAdapter("fs.default")}
    owner = MissionLifecycleOwner(log, mission_id=mid, observer=observer)

    engine = owner.build_effect_engine(registry, adapters)

    result = await engine.run(
        _manifest(),
        "fs.read",
        intended_change={"path": "/tmp/m14"},
        postconditions={"ok": True},
        idempotency_key="k-f-e15",
    )

    from jarvis.kernel.effect_envelope import EffectEnvelope
    assert isinstance(result, EffectEnvelope)
    assert result.verification.passed is True

    names = {span.name for span in exporter.get_finished_spans()}
    assert effect_span_name("execute") in names
    assert verify_span_name("postconditions") in names
    assert SPAN_EVENT in names
    assert len(exporter.get_finished_spans()) >= 3
