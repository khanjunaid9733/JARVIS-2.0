from __future__ import annotations

from pathlib import Path
import pytest

from jarvis.deployment.scheduler import AutonomousScheduler, ScheduledMission
from jarvis.kernel.event_log import EventLog
from jarvis.safety.estop import EStopLatch


@pytest.fixture
def temp_log(tmp_path: Path):
    db_file = tmp_path / "scheduler_log.db"
    return EventLog(db_path=db_file)


def test_scheduler_dispatches_due_mission(temp_log: EventLog):
    dispatched = []
    scheduler = AutonomousScheduler(
        event_log=temp_log,
        dispatcher=lambda m: dispatched.append(m.mission_id) or True,
    )

    mission = ScheduledMission(
        mission_id="m_telemetry_sync",
        name="Telemetry Sync",
        goal="Sync node telemetry",
        interval_seconds=10.0,
    )
    scheduler.schedule(mission)

    # Initial tick at t=0: last_run=0 so elapsed is 0, not due yet
    executed = scheduler.tick(now=5.0)
    assert len(executed) == 0

    # Advance time to t=10.0: now due!
    executed = scheduler.tick(now=10.0)
    assert executed == ["m_telemetry_sync"]
    assert len(dispatched) == 1
    assert mission.run_count == 1

    # Advance only 2s to t=12.0: not due
    assert len(scheduler.tick(now=12.0)) == 0

    # Advance to t=20.0: due again
    executed2 = scheduler.tick(now=20.0)
    assert executed2 == ["m_telemetry_sync"]
    assert mission.run_count == 2


def test_scheduler_respects_max_runs():
    dispatched = []
    scheduler = AutonomousScheduler(
        dispatcher=lambda m: dispatched.append(m.mission_id) or True,
    )

    mission = ScheduledMission(
        mission_id="m_calib",
        name="Calibrate IMU",
        goal="Run calibration",
        interval_seconds=5.0,
        max_runs=2,
    )
    scheduler.schedule(mission)

    scheduler.tick(now=5.0)
    assert mission.run_count == 1
    assert mission.enabled is True

    scheduler.tick(now=10.0)
    assert mission.run_count == 2
    assert mission.enabled is False  # Auto-disabled

    # Further ticks do not execute
    scheduler.tick(now=15.0)
    assert mission.run_count == 2
    assert len(dispatched) == 2


def test_scheduler_blocked_when_estop_tripped(temp_log: EventLog):
    safety = EStopLatch(event_log=temp_log)
    dispatched = []
    scheduler = AutonomousScheduler(
        event_log=temp_log,
        estop_latch=safety,
        dispatcher=lambda m: dispatched.append(m.mission_id) or True,
    )

    mission = ScheduledMission(
        mission_id="m_patrol",
        name="Physical Patrol",
        goal="Patrol perimeter with robot",
        interval_seconds=5.0,
        require_safety_normal=True,
    )
    scheduler.schedule(mission)

    # Trip physical safety plane
    safety.trip("Emergency stop switch engaged", source="switch")

    # Tick when due
    executed = scheduler.tick(now=5.0)
    assert len(executed) == 0
    assert len(dispatched) == 0
    assert mission.run_count == 0  # Not executed!

    # Check blocked audit event
    cur = temp_log._conn.execute(
        "SELECT * FROM events WHERE event_type = 'scheduler.mission_blocked_by_safety'"
    )
    assert cur.fetchone() is not None


def test_scheduler_unschedule_removes_mission():
    scheduler = AutonomousScheduler()
    mission = ScheduledMission(
        mission_id="m_temp",
        name="Temporary Task",
        goal="Short lived",
        interval_seconds=5.0,
    )
    scheduler.schedule(mission)
    assert scheduler.get_mission("m_temp") is not None

    removed = scheduler.unschedule("m_temp")
    assert removed is True
    assert scheduler.get_mission("m_temp") is None
    assert len(scheduler.list_missions()) == 0


def test_scheduler_events_appended_to_log(temp_log: EventLog):
    scheduler = AutonomousScheduler(event_log=temp_log)
    mission = ScheduledMission(
        mission_id="m_audit_test",
        name="Audit Test",
        goal="Test log emission",
        interval_seconds=5.0,
    )
    scheduler.schedule(mission)
    scheduler.tick(now=5.0)

    cur = temp_log._conn.execute(
        "SELECT event_type FROM events WHERE stream_id = 'scheduler' ORDER BY seq ASC"
    )
    events = [r["event_type"] for r in cur.fetchall()]
    assert "scheduler.mission_registered" in events
    assert "scheduler.mission_dispatched" in events
    assert temp_log.verify_chain()
