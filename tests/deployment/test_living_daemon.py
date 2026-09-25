from __future__ import annotations

from pathlib import Path
import time
import pytest

from jarvis.deployment.daemon import DaemonConfig, DaemonState, LivingDaemon
from jarvis.kernel.event_log import EventLog
from jarvis.safety.estop import EStopLatch


@pytest.fixture
def temp_log(tmp_path: Path):
    db_file = tmp_path / "daemon_test.db"
    return EventLog(db_path=db_file)


def test_daemon_start_and_stop_lifecycle(temp_log: EventLog):
    daemon = LivingDaemon(event_log=temp_log, config=DaemonConfig(enable_signal_handlers=False))
    assert daemon.state == DaemonState.UNINITIALIZED

    daemon.start(background=False)
    assert daemon.state == DaemonState.RUNNING
    assert daemon.uptime_seconds >= 0.0

    daemon.stop(reason="test_completed")
    assert daemon.state == DaemonState.STOPPED

    # Verify audit events
    cur = temp_log._conn.execute(
        "SELECT event_type FROM events WHERE stream_id = 'daemon' ORDER BY seq ASC"
    )
    events = [r["event_type"] for r in cur.fetchall()]
    assert "daemon.started" in events
    assert "daemon.stopped" in events
    assert temp_log.verify_chain()


def test_daemon_tick_advances_counter(temp_log: EventLog):
    called = []
    daemon = LivingDaemon(
        event_log=temp_log,
        config=DaemonConfig(enable_signal_handlers=False),
        on_tick=lambda: called.append(1),
    )
    daemon.start(background=False)

    res1 = daemon.tick()
    assert res1["ticked"] is True
    assert daemon.tick_count == 1
    assert len(called) == 1

    res2 = daemon.tick()
    assert res2["ticked"] is True
    assert daemon.tick_count == 2
    assert len(called) == 2

    daemon.stop()


def test_daemon_pause_and_resume(temp_log: EventLog):
    called = []
    daemon = LivingDaemon(
        event_log=temp_log,
        config=DaemonConfig(enable_signal_handlers=False),
        on_tick=lambda: called.append(1),
    )
    daemon.start(background=False)

    daemon.pause()
    assert daemon.state == DaemonState.PAUSED

    res = daemon.tick()
    assert res["ticked"] is True
    # In PAUSED mode, on_tick is suspended
    assert len(called) == 0

    daemon.resume()
    assert daemon.state == DaemonState.RUNNING
    daemon.tick()
    assert len(called) == 1

    daemon.stop()


def test_daemon_health_status_reporting(temp_log: EventLog):
    safety = EStopLatch(event_log=temp_log)
    daemon = LivingDaemon(
        event_log=temp_log,
        estop_latch=safety,
        config=DaemonConfig(node_id="workstation_alpha", enable_signal_handlers=False),
    )
    daemon.start(background=False)
    daemon.tick()

    health = daemon.health_status()
    assert health["node_id"] == "workstation_alpha"
    assert health["state"] == "running"
    assert health["healthy"] is True
    assert health["estop_tripped"] is False
    assert health["tick_count"] == 1
    assert health["total_events"] >= 1

    daemon.stop()


def test_daemon_safety_estop_correlation(temp_log: EventLog):
    safety = EStopLatch(event_log=temp_log)
    daemon = LivingDaemon(
        event_log=temp_log,
        estop_latch=safety,
        config=DaemonConfig(enable_signal_handlers=False),
    )
    daemon.start(background=False)

    assert daemon.health_status()["healthy"] is True

    # Trip physical safety plane
    safety.trip("Safety interlock switch opened", source="interlock")

    health = daemon.health_status()
    assert health["healthy"] is False
    assert health["estop_tripped"] is True
    assert health["safety_state"] == "estop"

    daemon.stop()


def test_daemon_heartbeat_event_appended(temp_log: EventLog):
    # Set heartbeat event interval very low (0.01s)
    daemon = LivingDaemon(
        event_log=temp_log,
        config=DaemonConfig(heartbeat_event_interval_seconds=0.01, enable_signal_handlers=False),
    )
    daemon.start(background=False)

    time.sleep(0.02)
    daemon.tick()

    cur = temp_log._conn.execute(
        "SELECT event_type FROM events WHERE event_type = 'daemon.heartbeat'"
    )
    assert cur.fetchone() is not None
    assert temp_log.verify_chain()

    daemon.stop()
