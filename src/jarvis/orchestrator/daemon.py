from __future__ import annotations

"""Supervisor daemon - the L6 loop's decision plane (§11 / §13 / §9).

The daemon owns the deterministic folds that turn journal state into the next
supervisor action. It performs NO effects on its own: every outcome is a datum
(TickReport), and termination / worktree-reset reach the world only through an
INJECTED effects seam - without a seam the outcome is declared, not executed
(the hermetic default, M3.4 RecoveryEngine precedent).

Three pure folds, all deterministic (same state + same wall clock -> identical
outcome):

    * lease_state        - §9's four observations the supervisor must tell
      apart: fresh / stale heartbeat, expired lease from a PRIOR supervisor,
      duplicate lease on the same task. STALLED and ORPHANED terminate;
      FRESH continues; the older of a duplicate pair is terminated.
    * recovery_decision  - §13's restart table applied to one dispatch trace:
      INTENT-only is UNKNOWN (kill by worker_id when known, reset, retry with a
      NEW dispatch_id), INTENT+STARTED is an ORPHAN (terminate, reset --hard,
      clean -fdx, retry), STARTED+COMPLETED is NORMAL (continue).
    * fold_ledger        - §7: the durable ledger is NEVER written directly; it
      is a pure fold over the journal. ACCEPT/REJECT/SUPERVISOR_INIT records
      project into the ledger snapshot.

Wall clock is an input (`now`), never a module read - tests drive transitions
without sleeping. No randomness, no process calls, no model calls, no I/O.

Additive law (M3.2-M3.5 precedent, re-applied): this module is STRICTLY
additive. Nothing below lives in a frozen module; no frozen module is
import-modified or touched. New milestone, new daemon.
"""

import enum
import time
from dataclasses import dataclass, field
from typing import Protocol, Sequence

# ---------------------------------------------------------------------------
# §9 - lease and heartbeat monitoring
# ---------------------------------------------------------------------------


class LeaseState(enum.Enum):
    """The four observations §9 requires the supervisor to tell apart."""

    FRESH = "fresh"
    STALLED = "stalled"
    ORPHANED = "orphaned"
    DUPLICATE = "duplicate"


@dataclass(frozen=True)
class Lease:
    """One worker lease, as granted (ORCHESTRATOR_ARCHITECTURE.md §9)."""

    lease_id: str
    task_id: str
    worker_id: str
    supervisor_instance_id: str
    expires_at: float
    renewed_at: float


def lease_state(
    lease: Lease,
    *,
    now: float,
    heartbeat_stale_after: float,
) -> LeaseState:
    """Classify one lease into one of the four §9 states.

    Deterministic in (lease, heartbeat_stale_after, now). Precedence:

        * duplicate - detected ONLY by the caller's partition pass (same
          task_id, different lease_id) and passed in via `duplicates`.
        * expired + supervisor_instance_id != current -> ORPHANED (a stale
          worker from a PRIOR supervisor; §9 row 3).
        * valid but heartbeat stale (now - renewed_at) > hnterval -> STALLED.
        * otherwise FRESH.
    """
    if not isinstance(lease, Lease):
        raise TypeError(f"lease_state expects a Lease, got {type(lease).__name__}")
    if lease.expires_at <= now:
        return LeaseState.ORPHANED
    if now - lease.renewed_at > heartbeat_stale_after:
        return LeaseState.STALLED
    return LeaseState.FRESH


def duplicate_lease_partition(leases: Sequence[Lease]) -> set[str]:
    """Return the lease_ids to terminate under §9 row 4: two workers, same
    task_id, different lease_id -> kill the OLDER lease (lower renewed_at; ties
    broken by lease_id) of each group of two or more."""
    by_task: dict[str, list[Lease]] = {}
    for lease in leases:
        by_task.setdefault(lease.task_id, []).append(lease)
    doomed: set[str] = set()
    for group in by_task.values():
        distinct = {l.lease_id for l in group}
        if len(distinct) > 1:
            older = min(group, key=lambda l: (l.renewed_at, l.lease_id))
            doomed.add(older.lease_id)
    return doomed


@dataclass(frozen=True)
class LeaseVerdict:
    """The daemon's datum for one lease: state + why + what the loop must do."""

    lease: Lease
    state: LeaseState
    reason: str
    action: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "action",
            "terminate"
            if self.state in (LeaseState.STALLED, LeaseState.ORPHANED, LeaseState.DUPLICATE)
            else "continue",
        )


def adjudicate_leases(
    leases: Sequence[Lease],
    *,
    current_supervisor_instance_id: str,
    now: float,
    heartbeat_stale_after: float,
) -> tuple[LeaseVerdict, ...]:
    """Adjudicate every lease into a verdict. ORPHANED requires the lease's
    recorded supervisor to differ from the current one; the partition pass
    supplies DUPLICATE for the older of each same-task group."""
    doomed = duplicate_lease_partition(leases)
    verdicts: list[LeaseVerdict] = []
    for lease in leases:
        if lease.lease_id in doomed:
            verdicts.append(
                LeaseVerdict(
                    lease,
                    LeaseState.DUPLICATE,
                    "older duplicate lease on task "
                    f"{lease.task_id} (same task_id, different lease_id)",
                )
            )
            continue
        state = lease_state(
            lease, now=now, heartbeat_stale_after=heartbeat_stale_after
        )
        if state is LeaseState.STALLED:
            reason = (
                f"lease valid but heartbeat stale (last renewed "
                f"{now - lease.renewed_at:.0f}s ago > {heartbeat_stale_after:.0f}s)"
            )
        elif state is LeaseState.ORPHANED:
            recorded = lease.supervisor_instance_id
            if recorded == current_supervisor_instance_id:
                reason = "lease expired, no renewed heartbeat; OWN lease"
            else:
                reason = (
                    f"lease expired with supervisor_instance_id {recorded!r} != "
                    f"current {current_supervisor_instance_id!r}; stale worker "
                    "from a prior supervisor"
                )
        else:
            reason = "lease valid and heartbeat fresh; worker genuinely running"
        verdicts.append(LeaseVerdict(lease, state, reason))
    return tuple(verdicts)


# ---------------------------------------------------------------------------
# §13 - dispatch trace recovery (the orphan table)
# ---------------------------------------------------------------------------


class RecoveryMode(enum.Enum):
    """§13 rows, applied to a folded dispatch trace."""

    UNKNOWN = "unknown"
    ORPHAN = "orphan"
    NORMAL = "normal"


@dataclass(frozen=True)
class DispatchTrace:
    """The fold of all journal records for one dispatch_id.

    Rows (§13):
        INTENT only                          -> UNKNOWN
        INTENT + STARTED                     -> ORPHAN
        STARTED + COMPLETED                  -> NORMAL
    """

    dispatch_id: str
    intent: bool
    started: bool
    completed: bool
    worker_id: str | None = None
    supervisor_instance_id: str | None = None

    @property
    def mode(self) -> RecoveryMode:
        if self.started and self.completed:
            return RecoveryMode.NORMAL
        if self.started:
            return RecoveryMode.ORPHAN
        return RecoveryMode.UNKNOWN

    @property
    def reason(self) -> str:
        if self.mode is RecoveryMode.NORMAL:
            return "INTENT + STARTED + COMPLETED; normal completion, continue"
        if self.mode is RecoveryMode.ORPHAN:
            return "INTENT + STARTED without COMPLETED; orphan worker, terminate & retry"
        return "INTENT recorded but no STARTED; spawn may or may not have happened"


@dataclass(frozen=True)
class RecoveryDecision:
    """What the loop must do for one dispatch trace. No effects are implied."""

    trace: DispatchTrace
    mode: RecoveryMode
    retry_with_new_dispatch_id: bool = True
    reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "retry_with_new_dispatch_id",
            not self.trace.completed,
        )


def fold_dispatches(records: Sequence[dict]) -> tuple[DispatchTrace, ...]:
    """Fold journal records into one trace per dispatch_id. Deterministic:
    the same records produce identical traces."""
    traces: dict[str, dict] = {}
    for rec in records:
        event = rec.get("event")
        dispatch_id = rec.get("dispatch_id")
        if dispatch_id is None:
            continue
        trace = traces.setdefault(
            dispatch_id,
            {
                "intent": False,
                "started": False,
                "completed": False,
                "worker_id": None,
                "supervisor_instance_id": None,
            },
        )
        if event == "DISPATCH_INTENT":
            trace["intent"] = True
            trace["supervisor_instance_id"] = rec.get("supervisor_instance_id")
        elif event == "DISPATCH_STARTED":
            trace["started"] = True
            trace["worker_id"] = rec.get("worker_id")
            trace["supervisor_instance_id"] = rec.get("supervisor_instance_id")
        elif event == "DISPATCH_COMPLETED":
            trace["completed"] = True
    ordered = sorted(traces.items())
    return tuple(
        DispatchTrace(dispatch_id=did, **data) for did, data in ordered
    )


def recovery_decision(trace: DispatchTrace) -> RecoveryDecision:
    """The loop's datum for one trace: UNKNOWN/ORPHAN retry with a NEW
    dispatch_id; NORMAL does not."""
    return RecoveryDecision(
        trace=trace,
        mode=trace.mode,
        reason=trace.reason,
    )


# ---------------------------------------------------------------------------
# §7 - the ledger is a pure fold over the journal (never written directly)
# ---------------------------------------------------------------------------

_EMPTY = ()


@dataclass(frozen=True)
class LedgerSnapshot:
    """The projection §7 maps the journal onto. `fold_ledger` is the ONLY
    way it is produced; scripts never write this shape directly."""

    frozen_packages: tuple[str, ...] = _EMPTY
    current_milestone: str | None = None
    baseline_commit: str | None = None
    current_commit: str | None = None
    last_known_good: str | None = None
    last_verify_exit: int | None = None
    current_blocker: str | None = None
    supervisor_instance_id: str | None = None


def fold_ledger(records: Sequence[dict]) -> LedgerSnapshot:
    """Pure fold over journal records into the §7 ledger projection.

    ACCEPT
        * push package onto frozen_packages (first occurrence wins the
          position; later ACCEPTs of the same package do not duplicate it)
        * current_milestone = package; last_verify_exit = exit
        * last_known_good = digest when exit == 0
    REJECT
        * current_blocker = package; last_verify_exit = exit
    SUPERVISOR_INIT
        * supervisor_instance_id = instance
    Any other record is ignored (the fold is total and order-sensitive).
    """
    frozen: list[str] = []
    milestone: str | None = None
    baseline: str | None = None
    current_commit: str | None = None
    last_good: str | None = None
    last_exit: int | None = None
    blocker: str | None = None
    sup_id: str | None = None
    seen: set[str] = set()
    for rec in records:
        event = rec.get("event")
        if event == "ACCEPT":
            pkg = rec.get("package")
            if pkg and pkg not in seen:
                frozen.append(pkg)
                seen.add(pkg)
            milestone = pkg
            exit_code = rec.get("exit")
            last_exit = exit_code
            if exit_code == 0:
                last_good = rec.get("digest")
                blocker = None
            baseline = rec.get("baseline_commit", baseline)
            current_commit = rec.get("current_commit", current_commit)
        elif event == "REJECT":
            blocker = rec.get("package")
            last_exit = rec.get("exit")
        elif event == "SUPERVISOR_INIT":
            sup_id = rec.get("instance")
    return LedgerSnapshot(
        frozen_packages=tuple(frozen),
        current_milestone=milestone,
        baseline_commit=baseline,
        current_commit=current_commit,
        last_known_good=last_good,
        last_verify_exit=last_exit,
        current_blocker=blocker,
        supervisor_instance_id=sup_id,
    )


def project_journal(entries: Sequence[dict]) -> tuple[dict, ...]:
    """Strip journal wrappers so a fold sees bare records. Accepts either the
    `record` payload directly or the {seq, ts, prev, record, hash} wrapper."""
    out: list[dict] = []
    for entry in entries:
        if isinstance(entry, dict) and "record" in entry:
            out.append(entry["record"])
        else:
            out.append(entry)
    return tuple(out)


# ---------------------------------------------------------------------------
# The tick - L6's deterministic decision plane
# ---------------------------------------------------------------------------


class Effects(Protocol):
    """INJECTED effect seam. Never ambient: hand this in or accept declared
    (unexecuted) outcomes. Mirrors M3.4's GitSeam convention."""

    def on_stale_lease(self, lease: Lease, *, reason: str) -> None: ...
    def on_orphaned_lease(self, lease: Lease, *, reason: str) -> None: ...
    def on_duplicate_lease(self, lease: Lease, *, reason: str) -> None: ...
    def on_unknown_dispatch(self, trace: DispatchTrace, *, reason: str) -> None: ...
    def on_orphan_dispatch(self, trace: DispatchTrace, *, reason: str) -> None: ...


@dataclass(frozen=True)
class TickReport:
    """Everything one supervisor wake decided. Effects happened ONLY where the
    injected Effects seam did them - the report itself writes nothing."""

    now: float
    ledger: LedgerSnapshot
    lease_verdicts: tuple[LeaseVerdict, ...]
    traces: tuple[DispatchTrace, ...]
    decisions: tuple[RecoveryDecision, ...]
    stalled: tuple[Lease, ...] = _EMPTY
    orphaned: tuple[Lease, ...] = _EMPTY
    duplicate: tuple[Lease, ...] = _EMPTY
    unknown: tuple[DispatchTrace, ...] = _EMPTY
    orphans: tuple[DispatchTrace, ...] = _EMPTY

    @property
    def to_terminate(self) -> tuple[LeaseVerdict, ...]:
        return tuple(v for v in self.lease_verdicts if v.action == "terminate")


class SupervisorDaemon:
    """The L6 loop body as a PURE decision function.

    run_tick(records, leases) -> TickReport  is fully deterministic. The
    wall clock is `now`, supplied by the caller. All lease/dispatch actions
    are DATA on the report; triggering them is the caller's (or the injected
    Effects seam's) business - never this class's.

    Hermetic default: no seam -> declared, not executed (M3.4 precedent).
    """

    __slots__ = ("_heartbeat_stale_after", "_current_instance", "_effects")

    def __init__(
        self,
        *,
        heartbeat_stale_after: float = 60.0,
        current_supervisor_instance_id: str | None = None,
        effects: Effects | None = None,
    ) -> None:
        self._heartbeat_stale_after = heartbeat_stale_after
        self._current_instance = current_supervisor_instance_id or _default_instance()
        self._effects = effects

    def run_tick(
        self,
        records: Sequence[dict],
        leases: Sequence[Lease] = (),
        *,
        now: float | None = None,
    ) -> TickReport:
        wall = now if now is not None else time.time()
        raw = project_journal(records)

        ledger = fold_ledger(raw)
        verdicts = adjudicate_leases(
            leases,
            current_supervisor_instance_id=self._current_instance,
            now=wall,
            heartbeat_stale_after=self._heartbeat_stale_after,
        )
        traces = fold_dispatches(raw)
        decisions = tuple(recovery_decision(t) for t in traces)

        stalled = tuple(v.lease for v in verdicts if v.state is LeaseState.STALLED)
        orphaned = tuple(v.lease for v in verdicts if v.state is LeaseState.ORPHANED)
        duplicate = tuple(v.lease for v in verdicts if v.state is LeaseState.DUPLICATE)
        unknown = tuple(d.trace for d in decisions if d.mode is RecoveryMode.UNKNOWN)
        orphans = tuple(d.trace for d in decisions if d.mode is RecoveryMode.ORPHAN)

        if self._effects is not None:
            for lease in duplicate:
                self._effects.on_duplicate_lease(lease, reason="older duplicate lease")
            for lease in orphaned:
                self._effects.on_orphaned_lease(lease, reason="expired + prior supervisor")
            for lease in stalled:
                self._effects.on_stale_lease(lease, reason="heartbeat stale")
            for trace in unknown:
                self._effects.on_unknown_dispatch(trace, reason="INTENT without STARTED")
            for trace in orphans:
                self._effects.on_orphan_dispatch(trace, reason="INTENT + STARTED without COMPLETED")

        return TickReport(
            now=wall,
            ledger=ledger,
            lease_verdicts=verdicts,
            traces=traces,
            decisions=decisions,
            stalled=stalled,
            orphaned=orphaned,
            duplicate=duplicate,
            unknown=unknown,
            orphans=orphans,
        )


def _default_instance() -> str:
    return "sup-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


__all__ = [
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
]