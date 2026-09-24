from __future__ import annotations

from pathlib import Path
import time
import pytest

from jarvis.kernel.event_log import EventLog
from jarvis.safety.estop import (
    EmergencyStopActiveError,
    EStopLatch,
    PhysicalCeilingExceededError,
    PhysicalCeilings,
    SafetyState,
)
from jarvis.safety.watchdog import HeartbeatWatchdog


@pytest.fixture
def temp_log(tmp_path: Path):
    db_file = tmp_path / "safety_log.db"
    return EventLog(db_path=db_file)


def test_estop_latch_trips_immediately():
    latch = EStopLatch()
    assert latch.state == SafetyState.NORMAL
    assert not latch.is_tripped()

    latch.trip("Operator hit hardware button", source="hardware_switch")
    assert latch.state == SafetyState.ESTOP
    assert latch.is_tripped()
    assert "hardware button" in latch.trip_reason


def test_estop_precedence_blocks_effect_dispatch():
    latch = EStopLatch()
    latch.assert_safe()  # Normal: does not raise

    latch.trip("Safety boundary crossed", source="sensor_proximity")
    with pytest.raises(EmergencyStopActiveError) as exc_info:
        latch.assert_safe()
    assert "Emergency Stop is ACTIVE" in str(exc_info.value)


def test_estop_latch_is_sticky_until_creator_reset():
    latch = EStopLatch()
    latch.trip("Collision hazard detected", source="ai_monitor")

    # Unauthorized reset attempt
    with pytest.raises(PermissionError):
        latch.reset(authorized_principal="agent_node_1")

    # Still tripped!
    assert latch.is_tripped()

    # Creator reset
    success = latch.reset(authorized_principal="creator")
    assert success is True
    assert not latch.is_tripped()
    assert latch.state == SafetyState.NORMAL
    latch.assert_safe()


def test_physical_ceilings_reject_excessive_velocity_or_power():
    ceilings = PhysicalCeilings(max_velocity_mps=1.5, max_power_watts=80.0, max_duty_cycle=0.85)

    # Valid parameters pass without exception
    ceilings.validate_parameters({"velocity_mps": 1.2, "power_watts": 50.0, "duty_cycle": 0.8})

    # Excessive velocity
    with pytest.raises(PhysicalCeilingExceededError) as exc:
        ceilings.validate_parameters({"velocity_mps": 2.5})
    assert "exceeds physical ceiling 1.5" in str(exc.value)

    # Excessive power
    with pytest.raises(PhysicalCeilingExceededError) as exc:
        ceilings.validate_parameters({"power_watts": 120.0})
    assert "exceeds physical ceiling 80.0" in str(exc.value)

    # Excessive PWM duty cycle
    with pytest.raises(PhysicalCeilingExceededError) as exc:
        ceilings.validate_parameters({"duty_cycle": 0.95})
    assert "exceeds physical ceiling 0.85" in str(exc.value)


def test_watchdog_timeout_triggers_fail_closed_estop():
    latch = EStopLatch()
    watchdog = HeartbeatWatchdog(estop_latch=latch, timeout_seconds=1.0)

    # Simulate elapsed time of 1.5s
    now = watchdog.last_pet + 1.5
    timed_out = watchdog.check_timeout(now=now)

    assert timed_out is True
    assert latch.is_tripped()
    assert latch.state == SafetyState.ESTOP
    assert "Watchdog timeout" in latch.trip_reason


def test_watchdog_petting_prevents_timeout():
    latch = EStopLatch()
    watchdog = HeartbeatWatchdog(estop_latch=latch, timeout_seconds=1.0)

    # Pet the watchdog before timeout
    start_time = watchdog.last_pet
    watchdog.pet()
    assert watchdog.last_pet >= start_time

    # Advance time only slightly
    now = watchdog.last_pet + 0.3
    assert not watchdog.check_timeout(now=now)
    assert not latch.is_tripped()
    assert latch.state == SafetyState.NORMAL


def test_e_stop_reaction_latency_under_50ms():
    latch = EStopLatch()
    start = time.perf_counter()

    # Trigger E-Stop and execute safety assertion check
    latch.trip("Latency verification probe", source="probe")
    is_safe = False
    try:
        latch.assert_safe()
        is_safe = True
    except EmergencyStopActiveError:
        pass

    duration_ms = (time.perf_counter() - start) * 1000.0

    assert not is_safe
    assert latch.is_tripped()
    # Invariant: Response time must be strictly under 50ms
    assert duration_ms < 50.0, f"E-Stop latency {duration_ms:.2f}ms exceeded 50ms budget!"


def test_safety_event_logging(temp_log: EventLog):
    latch = EStopLatch(event_log=temp_log)
    latch.trip("Thermal runaway on Motor 2", source="thermal_sensor")

    # Verify event appended to 'safety' stream
    cur = temp_log._conn.execute("SELECT * FROM events WHERE stream_id = 'safety'")
    events = cur.fetchall()
    assert len(events) == 1

    ev = events[0]
    assert ev["event_type"] == "safety.estop_triggered"
    assert ev["principal_id"] == "thermal_sensor"

    # Now reset as creator and verify second event
    latch.reset(authorized_principal="creator")
    cur2 = temp_log._conn.execute(
        "SELECT * FROM events WHERE stream_id = 'safety' ORDER BY seq ASC"
    )
    events2 = cur2.fetchall()
    assert len(events2) == 2
    assert events2[1]["event_type"] == "safety.estop_reset"
    assert events2[1]["principal_id"] == "creator"
    assert temp_log.verify_chain()
