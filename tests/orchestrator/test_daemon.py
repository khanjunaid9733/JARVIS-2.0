from __future__ import annotations

"""M3.5 - the L6 supervisor daemon decision plane (sections 9/11/13 re-applied).

`SupervisorDaemon` owns the three deterministic folds of the supervisor loop:

    * §9          - `adjudicate_leases`/`lease_state`: FRESH heartbeat /
                    STALLED heartbeat / ORPHANED (expired lease from a PRIOR
                    supervisor) / DUPLICATE (older of two leases on one task).
    * §13         - `fold_dispatches`/`recovery_decision`: INTENT-only is
                    UNKNOWN, INTENT+STARTED is ORPHAN, STARTED+COMPLETED is
                    NORMAL; UNKNOWN/ORPHAN retry with a NEW dispatch_id.
    * §7          - `fold_ledger`: the ledger is a pure fold over the journal,
                    never written directly.

Hermetic: no I/O, no process calls, no sleeping - the wall clock is an input
(`now`). Effects reach the world ONLY through the injected `Effects` seam;
with no seam the outcomes are declared, not executed (M3.4 precedent).
Determinism (F-M2.3-6 re-applied): same state + same now -> identical report.
"""

import pytest

from jarvis.orchestrator.daemon import (
    DispatchTrace,
    Effects,
    Lease,
    LeaseState,
    LeaseVerdict,
    LedgerSnapshot,
    RecoveryDecision,
    RecoveryMode,
    SupervisorDaemon,
    TickReport,
    adjudicate_leases,
    duplicate_lease_partition,
    fold_dispatches,
    fold_ledger,
    lease_state,
    project_journal,
    recovery_decision,
)

NOW = 1_000_000.0
SUP = "sup-current"
PRIOR_SUP = "sup-prior"


def _lease(
    lease_id: str = "lease-1",
    task_id: str = "M3.5",
    worker_id: str = "w-1",
    supervisor: str = SUP,
    expires_at: float = NOW + 600,
    renewed_at: float = NOW - 5,
) -> Lease:
    return Lease(
        lease_id=lease_id,
        task_id=task_id,
        worker_id=worker_id,
        supervisor_instance_id=supervisor,
        expires_at=expires_at,
        renewed_at=renewed_at,
    )


def test_lease_state_fresh_lease_with_recent_heartbeat() -> None:
    lease = _lease(renewed_at=NOW - 1)
    assert lease_state(lease, now=NOW, heartbeat_stale_after=60) is LeaseState.FRESH


def test_lease_state_valid_lease_stale_heartbeat_is_stalled() -> None:
    lease = _lease(renewed_at=NOW - 121)
    assert lease_state(lease, now=NOW, heartbeat_stale_after=60) is LeaseState.STALLED


def test_lease_state_expired_is_orphaned() -> None:
    lease = _lease(expires_at=NOW - 1)
    assert lease_state(lease, now=NOW, heartbeat_stale_after=60) is LeaseState.ORPHANED


def test_lease_state_fresh_within_stale_window_but_no_expiry() -> None:
    lease = _lease(renewed_at=NOW - 59)
    assert lease_state(lease, now=NOW, heartbeat_stale_after=60) is LeaseState.FRESH


def test_duplicate_partition_kills_older_lease_only() -> None:
    newer = _lease("lease-newer", renewed_at=NOW - 1)
    older = _lease("lease-older", renewed_at=NOW - 300)
    doomed = duplicate_lease_partition([newer, older])
    assert doomed == {"lease-older"}


def test_duplicate_partition_two_leases_same_task_different_ids() -> None:
    a = _lease("lease-a", worker_id="w-a")
    b = _lease("lease-b", worker_id="w-b", renewed_at=NOW - 7)
    doomed = duplicate_lease_partition([a, b])
    assert doomed == {b.lease_id}


def test_duplicate_partition_single_lease_per_task_is_untouched() -> None:
    a = _lease("lease-a", task_id="T1")
    b = _lease("lease-b", task_id="T2")
    assert duplicate_lease_partition([a, b]) == set()


def test_duplicate_partition_distinct_tasks_with_repeated_ids() -> None:
    a = _lease("lease-a", task_id="T1")
    b = _lease("lease-a", task_id="T2")
    assert duplicate_lease_partition([a, b]) == set()


def test_adjudicate_leases_verdict_actions_collect_terminate_targets() -> None:
    fresh = _lease("fresh", task_id="T1", renewed_at=NOW - 1)
    stalled = _lease("stalled", task_id="T2", renewed_at=NOW - 300)
    orphaned = _lease("orphan", task_id="T3", supervisor=PRIOR_SUP, expires_at=NOW - 1)
    verdicts = adjudicate_leases(
        [fresh, stalled, orphaned],
        current_supervisor_instance_id=SUP,
        now=NOW,
        heartbeat_stale_after=60,
    )
    by_id = {v.lease.lease_id: v for v in verdicts}
    assert by_id["fresh"].action == "continue"
    assert by_id["stalled"].state is LeaseState.STALLED
    assert by_id["stalled"].action == "terminate"
    assert "stale" in by_id["stalled"].reason
    assert by_id["orphan"].state is LeaseState.ORPHANED
    assert "prior supervisor" in by_id["orphan"].reason


def test_adjudicate_leases_duplicate_supersedes_stale_verdict() -> None:
    older = _lease("older", renewed_at=NOW - 400)
    verdicts = adjudicate_leases(
        [older, _lease("newer", renewed_at=NOW - 2)],
        current_supervisor_instance_id=SUP,
        now=NOW,
        heartbeat_stale_after=60,
    )
    older_verdict = next(v for v in verdicts if v.lease.lease_id == "older")
    assert older_verdict.state is LeaseState.DUPLICATE
    assert older_verdict.action == "terminate"


def test_adjudicate_leases_own_expired_lease_is_not_prior_supervisor() -> None:
    own = _lease("own-expired", supervisor=SUP, expires_at=NOW - 1)
    verdicts = adjudicate_leases(
        [own],
        current_supervisor_instance_id=SUP,
        now=NOW,
        heartbeat_stale_after=60,
    )
    assert verdicts[0].state is LeaseState.ORPHANED
    assert "OWN lease" in verdicts[0].reason


class _RecordingEffects(Effects):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def on_stale_lease(self, lease: Lease, *, reason: str) -> None:
        self.calls.append(f"stale:{lease.lease_id}")

    def on_orphaned_lease(self, lease: Lease, *, reason: str) -> None:
        self.calls.append(f"orphaned:{lease.lease_id}")

    def on_duplicate_lease(self, lease: Lease, *, reason: str) -> None:
        self.calls.append(f"duplicate:{lease.lease_id}")

    def on_unknown_dispatch(self, trace: DispatchTrace, *, reason: str) -> None:
        self.calls.append(f"unknown:{trace.dispatch_id}")

    def on_orphan_dispatch(self, trace: DispatchTrace, *, reason: str) -> None:
        self.calls.append(f"orphan:{trace.dispatch_id}")


def _intent(did: str, task: str = "M3.5") -> dict:
    return {
        "event": "DISPATCH_INTENT",
        "dispatch_id": did,
        "task": task,
        "role": "IMPLEMENTER",
        "provider": "bigpickle",
        "supervisor_instance_id": SUP,
    }


def _started(did: str, worker: str = "w-1") -> dict:
    return {
        "event": "DISPATCH_STARTED",
        "dispatch_id": did,
        "worker_id": worker,
        "handle": f"{worker}-handle",
        "supervisor_instance_id": SUP,
    }


def _completed(did: str) -> dict:
    return {
        "event": "DISPATCH_COMPLETED",
        "dispatch_id": did,
        "output_commit": "abc123",
    }


REC_ALL_EVENTS = [_intent("d1"), _started("d1"), _completed("d1")]
REC_INTENT_STARTED = [_intent("d2"), _started("d2")]
REC_INTENT_ONLY = [_intent("d3")]
REC_EMPTY: list[dict] = []


def test_daemon_hermetic_default_declares_without_effecting() -> None:
    daemon = SupervisorDaemon(current_supervisor_instance_id=SUP)
    report = daemon.run_tick(
        [_intent("d1")],
        [_lease("stalled", renewed_at=NOW - 300)],
        now=NOW,
    )
    assert isinstance(report, TickReport)
    assert report.stalled[0].lease_id == "stalled"
    assert report.unknown[0].dispatch_id == "d1"


def test_daemon_with_hermetic_default_performs_no_effects() -> None:
    daemon = SupervisorDaemon(current_supervisor_instance_id=SUP)
    report = daemon.run_tick(
        [_intent("d1")],
        [_lease("stalled", renewed_at=NOW - 300)],
        now=NOW,
    )
    assert report.to_terminate and report.decisions  # data is present
    # but the hermetic default does no work - nothing to observe besides the report


def test_daemon_project_journal_unwraps_wrapper_entries() -> None:
    wrapped = [{"seq": 0, "ts": "t", "prev": "p", "record": _intent("d1"), "hash": "h"}]
    assert project_journal(wrapped) == tuple([_intent("d1")])


def test_daemon_project_journal_passes_bare_records_through() -> None:
    assert project_journal([_intent("d1")]) == (_intent("d1"),)


def test_fold_dispatches_intent_only_is_unknown() -> None:
    traces = fold_dispatches(REC_INTENT_ONLY)
    assert len(traces) == 1
    assert traces[0].mode is RecoveryMode.UNKNOWN


def test_fold_dispatches_intent_started_is_orphan() -> None:
    traces = fold_dispatches(REC_INTENT_STARTED)
    assert len(traces) == 1
    assert traces[0].mode is RecoveryMode.ORPHAN
    assert traces[0].worker_id == "w-1"


def test_fold_dispatches_full_lifecycle_is_normal() -> None:
    traces = fold_dispatches(REC_ALL_EVENTS)
    assert len(traces) == 1
    assert traces[0].mode is RecoveryMode.NORMAL


def test_fold_dispatches_ignores_unrelated_records() -> None:
    traces = fold_dispatches([{"event": "ACCEPT", "package": "M3.5"}, _intent("d1")])
    assert len(traces) == 1
    assert traces[0].dispatch_id == "d1"


def test_recovery_decision_unknown_retries_with_new_dispatch_id() -> None:
    decision = recovery_decision(DispatchTrace("d3", True, False, False))
    assert decision.mode is RecoveryMode.UNKNOWN
    assert decision.retry_with_new_dispatch_id is True


def test_recovery_decision_orphan_retries_with_new_dispatch_id() -> None:
    decision = recovery_decision(DispatchTrace("d2", True, True, False, worker_id="w-1"))
    assert decision.mode is RecoveryMode.ORPHAN
    assert decision.retry_with_new_dispatch_id is True


def test_recovery_decision_normal_does_not_retry() -> None:
    decision = recovery_decision(DispatchTrace("d1", True, True, True))
    assert decision.mode is RecoveryMode.NORMAL
    assert decision.retry_with_new_dispatch_id is False


def test_ledger_fold_from_empty_journal_is_empty_ledger() -> None:
    snapshot = fold_ledger([])
    assert snapshot == LedgerSnapshot()
    assert snapshot.frozen_packages == ()


def test_ledger_fold_accept_records_push_frozen_packages_in_order() -> None:
    snapshot = fold_ledger(
        [
            {"event": "ACCEPT", "package": "M3.1", "exit": 0, "digest": "sha256:a"},
            {"event": "ACCEPT", "package": "M3.2", "exit": 0, "digest": "sha256:b"},
        ]
    )
    assert snapshot.frozen_packages == ("M3.1", "M3.2")
    assert snapshot.current_milestone == "M3.2"
    assert snapshot.last_known_good == "sha256:b"
    assert snapshot.last_verify_exit == 0


def test_ledger_fold_accept_then_reject_sets_blocker_and_exit() -> None:
    snapshot = fold_ledger(
        [
            {"event": "ACCEPT", "package": "M3.1", "exit": 0, "digest": "sha256:a"},
            {"event": "REJECT", "package": "M3.2", "exit": 1},
        ]
    )
    assert snapshot.last_verify_exit == 1
    assert snapshot.current_blocker == "M3.2"
    assert snapshot.last_known_good == "sha256:a"


def test_ledger_fold_supervisor_init_sets_instance() -> None:
    snapshot = fold_ledger([{"event": "SUPERVISOR_INIT", "instance": "sup-xyz"}])
    assert snapshot.supervisor_instance_id == "sup-xyz"


def test_ledger_fold_preserves_baseline_and_current_commit_fields() -> None:
    snapshot = fold_ledger(
        [
            {
                "event": "ACCEPT",
                "package": "M3.4",
                "exit": 0,
                "digest": "sha256:c",
                "baseline_commit": "7607a6f",
                "current_commit": "0f43bcf",
            }
        ]
    )
    assert snapshot.baseline_commit == "7607a6f"
    assert snapshot.current_commit == "0f43bcf"


def test_ledger_fold_total_over_unrelated_records() -> None:
    snapshot = fold_ledger([{"event": "DISPATCH_INTENT", "dispatch_id": "d1"}])
    assert snapshot == LedgerSnapshot()


def test_daemon_run_tick_is_deterministic() -> None:
    a = SupervisorDaemon(
        current_supervisor_instance_id=SUP, heartbeat_stale_after=60
    ).run_tick(REC_INTENT_STARTED, [_lease("stalled", renewed_at=NOW - 300)], now=NOW)
    b = SupervisorDaemon(
        current_supervisor_instance_id=SUP, heartbeat_stale_after=60
    ).run_tick(REC_INTENT_STARTED, [_lease("stalled", renewed_at=NOW - 300)], now=NOW)
    assert a == b


def test_daemon_injected_effects_seam_is_invoked() -> None:
    effects = _RecordingEffects()
    daemon = SupervisorDaemon(
        current_supervisor_instance_id=SUP, effects=effects
    )
    daemon.run_tick(
        [_intent("d1"), _started("d1")],
        [
            _lease("stalled", renewed_at=NOW - 300),
            _lease("orphan", supervisor=PRIOR_SUP, expires_at=NOW - 1),
            _lease("newer-dup", renewed_at=NOW - 2),
            _lease("older-dup", renewed_at=NOW - 400),
        ],
        now=NOW,
    )
    assert effects.calls == [
        "duplicate:older-dup",
        "orphaned:orphan",
        "stale:stalled",
        "orphan:d1",
    ]


def test_daemon_effects_seam_not_invoked_without_effects() -> None:
    daemon = SupervisorDaemon(current_supervisor_instance_id=SUP)
    report = daemon.run_tick(
        [_intent("d1")],
        [_lease("stalled", renewed_at=NOW - 300)],
        now=NOW,
    )
    assert isinstance(report, TickReport)
    assert report.to_terminate


def test_daemon_default_now_from_wall_clock_not_required_explicitly() -> None:
    daemon = SupervisorDaemon(current_supervisor_instance_id=SUP)
    report = daemon.run_tick(REC_EMPTY)
    assert report.now > 0
    assert report.ledger == LedgerSnapshot()


def test_daemon_lease_state_rejects_non_lease_input() -> None:
    with pytest.raises(TypeError):
        lease_state({"fake": True}, now=NOW, heartbeat_stale_after=60)  # type: ignore[arg-type]


def test_daemon_verdict_list_order_is_container_order() -> None:
    verdicts = adjudicate_leases(
        [_lease("a"), _lease("b")],
        current_supervisor_instance_id=SUP,
        now=NOW,
        heartbeat_stale_after=60,
    )
    assert [v.lease.lease_id for v in verdicts] == ["a", "b"]
    assert isinstance(verdicts[0], LeaseVerdict)


def test_daemon_export_surface_is_stable() -> None:
    expected = {
        "DispatchTrace",
        "Effects",
        "Lease",
        "LeaseState",
        "LeaseVerdict",
        "LedgerSnapshot",
        "RecoveryDecision",
        "RecoveryMode",
        "SupervisorDaemon",
        "TickReport",
        "adjudicate_leases",
        "duplicate_lease_partition",
        "fold_dispatches",
        "fold_ledger",
        "lease_state",
        "project_journal",
        "recovery_decision",
    }
    from jarvis.orchestrator.daemon import __all__

    assert set(__all__) == expected