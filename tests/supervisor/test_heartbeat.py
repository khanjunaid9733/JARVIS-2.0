from __future__ import annotations

"""M2.5 - heartbeat / observer seam: liveness is evidence, never narration (L4).

A worker's heartbeat is a FRESH observed datum on the live surface, delivered
through the Observer seam (Observe -> EvidenceLedger). It is NEVER a memory
claim: a stale heartbeat means "lost contact", which is a DECLARED fact that
feeds the ladder as RESTART (no fresh evidence) or HOLD via the STALLED event.
The supervisor makes no model call to know a worker is stopped - it folds the
ledger of what an observer ACTUALLY returned. Hermetic: the observer below is
an injected seam; there is no clock, no I/O, no ambient read in these tests.
"""

import pytest

from jarvis.supervisor import (
    Evidence,
    EvidenceLedger,
    EvidencePrecedence,
    EvidenceSource,
    LifecycleEvent,
    LifecycleState,
    Observer,
    RecoveryAction,
    RecoveryPolicy,
    Supervisor,
    TaskLifecycle,
    decide_recovery,
)

ISO = "2026-09-21T00:00:00.000Z"
STALE_ISO = "2026-09-21T00:00:04.000Z"
NOW_ISO = "2026-09-21T00:00:10.000Z"


class _FreshObserver(Observer):
    """Injected seam: a live worker heartbeat represented as a fresh
    FILESYSTEM-level datum (a measured machine fact, the top rung)."""

    def __init__(self, observed_at: str) -> None:
        self._observed_at = observed_at

    def observe(self) -> EvidenceLedger:
        return EvidenceLedger(
            observed_at=self._observed_at,
            entries=(
                Evidence.declare(
                    source=EvidenceSource.TOOL_OUTPUT,
                    summary="heartbeat: worker w-7f3a alive",
                    observed_at=self._observed_at,
                ),
                Evidence.declare(
                    source=EvidenceSource.FILESYSTEM,
                    summary="fresh system datum: exit 0 present",
                    observed_at=self._observed_at,
                ),
            ),
        )


class _SilentObserver(Observer):
    """Injected seam: no heartbeat has been observed - lost contact."""

    def __init__(self, observed_at: str) -> None:
        self._observed_at = observed_at

    def observe(self) -> EvidenceLedger:
        return EvidenceLedger(
            observed_at=self._observed_at,
            entries=(
                Evidence.declare(
                    source=EvidenceSource.AGENT_MEMORY,
                    summary="no live datum; nothing fresh measured",
                    observed_at=self._observed_at,
                ),
            ),
        )


def test_observe_is_a_hermetic_evidence_delivery() -> None:
    """The observer returns a ledger of what is ACTUALLY true (fresh bytes),
    never a status string the worker narrates."""
    obs = _FreshObserver(NOW_ISO)
    ledger = obs.observe()
    assert isinstance(ledger, EvidenceLedger)
    authority = ledger.authority()
    assert authority is not None
    assert authority.source is EvidenceSource.FILESYSTEM


def test_fresh_heartbeat_supports_retry() -> None:
    """A live heartbeat (fresh measured datum) is recovery-relevant: the ladder
    may RETRY rather than restart."""
    ledger = _FreshObserver(NOW_ISO).observe()
    plan = decide_recovery(
        state=LifecycleState.FAILED,
        ledger=ledger,
        attempts_used=1,
        policy=RecoveryPolicy(max_attempts=3, rollback_available=True),
        reason="fresh heartbeat present",
    )
    assert plan.action is RecoveryAction.RETRY
    assert plan.evidence is not None


def test_stale_heartbeat_means_restart_not_retry() -> None:
    """Silent observer -> no fresh datum -> RESTART from a clean context. The
    ladder does NOT trust a memory claim that the worker was fine a moment ago."""
    ledger = _SilentObserver(STALE_ISO).observe()
    plan = decide_recovery(
        state=LifecycleState.FAILED,
        ledger=ledger,
        attempts_used=0,
        policy=RecoveryPolicy(max_attempts=3, rollback_available=True),
        reason="heartbeat stale; lost contact",
    )
    assert plan.action is RecoveryAction.RESTART


def test_stalled_event_holds_a_proposed_worker() -> None:
    """L4: a stalled worker without progress is declared HELD, not silently
    carried forward."""
    lc = TaskLifecycle(state=LifecycleState.PROPOSED)
    held = lc.apply(LifecycleEvent.STALLED)
    assert held.state is LifecycleState.HELD


def test_supervisor_consumes_observed_ledger_via_seam() -> None:
    """Supervisor wires observe -> fold: the current ledger after a decision
    includes the observer's fresh datum plus the worker claim (append-only)."""
    obs = _FreshObserver(NOW_ISO)
    sup = Supervisor(ledger=obs.observe())
    decision = sup.decide(worker_claim=True, observed_at=NOW_ISO)
    assert decision.ledger.highest().source is EvidenceSource.FILESYSTEM
    assert len(decision.ledger.entries) == 3  # 2 observed + 1 worker claim


def test_heartbeat_freshness_is_timestamped_data() -> None:
    """Freshness is encoded IN the datum (observed_at), never read from an
    ambient wall clock."""
    fresh = Evidence.declare(
        source=EvidenceSource.TOOL_OUTPUT,
        summary="heartbeat alive",
        observed_at=NOW_ISO,
    )
    stale = Evidence.declare(
        source=EvidenceSource.TOOL_OUTPUT,
        summary="heartbeat = dead",
        observed_at=STALE_ISO,
    )
    assert fresh.observed_at == NOW_ISO
    assert stale.source is fresh.source
    assert fresh.precedence is EvidencePrecedence.TOOL_OUTPUT
    # Same source, different datums: precedence alone cannot order them - the
    # observed_at is the live-flag. The decision (recovery) must weigh it.
    assert stale.observed_at != fresh.observed_at