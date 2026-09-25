"""Tests for Background Headless Computer-Use Seam (Milestone M7.2)."""

from pathlib import Path
import pytest

from jarvis.effects.computer_use import (
    ComputerUseExecutor,
    ComputerUseSecurityError,
    DeliveryMode,
    GUIAction,
    GUIActionType,
    MockComputerUseDriver,
)
from jarvis.kernel.event_log import EventLog
from jarvis.safety.estop import EStopLatch, EmergencyStopActiveError


@pytest.fixture
def mock_driver() -> MockComputerUseDriver:
    return MockComputerUseDriver()


@pytest.fixture
def event_log(tmp_path: Path) -> EventLog:
    return EventLog(db_path=tmp_path / "test_computer_use.db")


@pytest.fixture
def estop_latch(event_log: EventLog) -> EStopLatch:
    return EStopLatch(event_log=event_log)


def test_headless_action_execution(mock_driver: MockComputerUseDriver, event_log: EventLog):
    executor = ComputerUseExecutor(driver=mock_driver, event_log=event_log)

    action = GUIAction(
        action_type=GUIActionType.CLICK,
        delivery_mode=DeliveryMode.BACKGROUND_HEADLESS,
        target_window_title="Web Browser",
        target_hwnd=1003,
        coordinates=(250, 400),
    )

    success = executor.execute(action)
    assert success is True
    assert len(mock_driver.executed_actions) == 1
    assert mock_driver.executed_actions[0].action_id == action.action_id
    assert mock_driver.executed_actions[0].delivery_mode == DeliveryMode.BACKGROUND_HEADLESS


def test_type_and_key_action_execution(mock_driver: MockComputerUseDriver):
    executor = ComputerUseExecutor(driver=mock_driver)

    type_act = GUIAction(
        action_type=GUIActionType.TYPE_TEXT,
        text_payload="Hello JARVIS",
    )
    key_act = GUIAction(
        action_type=GUIActionType.PRESS_KEY,
        key_name="Enter",
    )

    assert executor.execute(type_act) is True
    assert executor.execute(key_act) is True
    assert len(mock_driver.executed_actions) == 2


def test_estop_blocks_gui_action(
    mock_driver: MockComputerUseDriver,
    event_log: EventLog,
    estop_latch: EStopLatch,
):
    executor = ComputerUseExecutor(
        driver=mock_driver,
        event_log=event_log,
        estop_latch=estop_latch,
    )

    # Trip the Emergency Stop
    estop_latch.trip(reason="Physical mouse collision detected")

    action = GUIAction(action_type=GUIActionType.CLICK)
    with pytest.raises(EmergencyStopActiveError):
        executor.execute(action)

    assert len(mock_driver.executed_actions) == 0

    # Verify blocked audit event logged
    events = event_log.replay()
    event_types = [e.event_type for e in events]
    assert "computer_use.action_blocked_by_safety" in event_types


def test_foreground_restriction_enforcement(mock_driver: MockComputerUseDriver):
    # Foreground delivery disallowed
    executor = ComputerUseExecutor(driver=mock_driver, allow_foreground=False)

    action = GUIAction(
        action_type=GUIActionType.CLICK,
        delivery_mode=DeliveryMode.FOREGROUND_EMULATED,
    )

    with pytest.raises(ComputerUseSecurityError):
        executor.execute(action)

    assert len(mock_driver.executed_actions) == 0


def test_action_audit_event_emission(
    mock_driver: MockComputerUseDriver,
    event_log: EventLog,
):
    executor = ComputerUseExecutor(driver=mock_driver, event_log=event_log)

    action = GUIAction(
        action_type=GUIActionType.CLICK,
        coordinates=(100, 200),
    )
    executor.execute(action)

    events = event_log.replay()
    assert len(events) == 1
    assert events[0].event_type == "computer_use.action_executed"
    assert events[0].payload["coordinates"] == [100, 200]


def test_driver_failure_handling(
    mock_driver: MockComputerUseDriver,
    event_log: EventLog,
):
    mock_driver.set_should_fail(True)
    executor = ComputerUseExecutor(driver=mock_driver, event_log=event_log)

    action = GUIAction(action_type=GUIActionType.CLICK)
    success = executor.execute(action)

    assert success is False
    events = event_log.replay()
    assert events[0].event_type == "computer_use.action_failed"
