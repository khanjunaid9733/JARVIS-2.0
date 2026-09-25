"""Tests for Closed-Loop Autonomous Computer-Use Engine (Milestone M7.5)."""

from pathlib import Path
import pytest

from jarvis.effects.computer_use import (
    ComputerUseExecutor,
    DeliveryMode,
    GUIAction,
    GUIActionType,
    MockComputerUseDriver,
)
from jarvis.kernel.computer_use import (
    ClosedLoopComputerUseEngine,
    ComputerUsePlan,
    ExecutionStatus,
)
from jarvis.kernel.event_log import EventLog
from jarvis.perception.screen import (
    MockScreenGrabber,
    ScreenPerceptionEngine,
)
from jarvis.safety.estop import EStopLatch
from jarvis.ui.overlay import SpatialOverlayEngine


@pytest.fixture
def mock_grabber() -> MockScreenGrabber:
    return MockScreenGrabber(
        width=1920,
        height=1080,
        initial_data=b"desktop_initial_state",
        active_window_title="Settings Window",
    )


@pytest.fixture
def perception_engine(mock_grabber: MockScreenGrabber) -> ScreenPerceptionEngine:
    return ScreenPerceptionEngine(grabber=mock_grabber)


@pytest.fixture
def mock_driver() -> MockComputerUseDriver:
    return MockComputerUseDriver()


@pytest.fixture
def event_log(tmp_path: Path) -> EventLog:
    return EventLog(db_path=tmp_path / "test_closed_loop.db")


@pytest.fixture
def estop_latch(event_log: EventLog) -> EStopLatch:
    return EStopLatch(event_log=event_log)


@pytest.fixture
def computer_use_executor(
    mock_driver: MockComputerUseDriver,
    event_log: EventLog,
    estop_latch: EStopLatch,
) -> ComputerUseExecutor:
    return ComputerUseExecutor(
        driver=mock_driver,
        event_log=event_log,
        estop_latch=estop_latch,
    )


@pytest.fixture
def overlay_engine(
    event_log: EventLog,
    estop_latch: EStopLatch,
) -> SpatialOverlayEngine:
    return SpatialOverlayEngine(
        event_log=event_log,
        estop_latch=estop_latch,
    )


def test_closed_loop_execution_success(
    perception_engine: ScreenPerceptionEngine,
    computer_use_executor: ComputerUseExecutor,
    overlay_engine: SpatialOverlayEngine,
    event_log: EventLog,
    mock_driver: MockComputerUseDriver,
):
    engine = ClosedLoopComputerUseEngine(
        perception_engine=perception_engine,
        computer_use_executor=computer_use_executor,
        overlay_engine=overlay_engine,
        event_log=event_log,
    )

    plan = ComputerUsePlan(
        goal="Open network settings and toggle adapter",
        steps=[
            GUIAction(
                action_type=GUIActionType.CLICK,
                delivery_mode=DeliveryMode.BACKGROUND_HEADLESS,
                coordinates=(300, 150),
            ),
            GUIAction(
                action_type=GUIActionType.TYPE_TEXT,
                delivery_mode=DeliveryMode.BACKGROUND_HEADLESS,
                text_payload="Ethernet",
            ),
        ],
    )

    result = engine.execute_plan(plan)

    assert result.status == ExecutionStatus.COMPLETED
    assert len(result.steps) == 2
    assert result.steps[0].verification_passed is True
    assert result.steps[1].verification_passed is True
    assert len(mock_driver.executed_actions) == 2

    # Overlays must be cleared post-execution
    assert len(overlay_engine.active_highlights) == 0
    assert overlay_engine.active_pointer is None

    # EventLog verification
    events = event_log.replay()
    types = [e.event_type for e in events]
    assert "computer_use.plan_started" in types
    assert "computer_use.plan_completed" in types


def test_closed_loop_safety_blocking(
    perception_engine: ScreenPerceptionEngine,
    computer_use_executor: ComputerUseExecutor,
    estop_latch: EStopLatch,
    mock_driver: MockComputerUseDriver,
):
    engine = ClosedLoopComputerUseEngine(
        perception_engine=perception_engine,
        computer_use_executor=computer_use_executor,
        estop_latch=estop_latch,
    )

    # Trip the safety latch before execution
    estop_latch.trip(reason="Creator physical mouse motion detected")

    plan = ComputerUsePlan(
        goal="Automated click under safety",
        steps=[
            GUIAction(action_type=GUIActionType.CLICK, coordinates=(100, 100)),
        ],
    )

    result = engine.execute_plan(plan)

    assert result.status == ExecutionStatus.BLOCKED_BY_SAFETY
    assert len(mock_driver.executed_actions) == 0


def test_closed_loop_aborts_on_step_failure(
    perception_engine: ScreenPerceptionEngine,
    computer_use_executor: ComputerUseExecutor,
    mock_driver: MockComputerUseDriver,
):
    engine = ClosedLoopComputerUseEngine(
        perception_engine=perception_engine,
        computer_use_executor=computer_use_executor,
    )

    # Configure driver to fail
    mock_driver.set_should_fail(True)

    plan = ComputerUsePlan(
        goal="Attempt failing action",
        steps=[
            GUIAction(action_type=GUIActionType.CLICK),
            GUIAction(action_type=GUIActionType.TYPE_TEXT, text_payload="unreached"),
        ],
    )

    result = engine.execute_plan(plan)

    assert result.status == ExecutionStatus.FAILED
    assert len(result.steps) == 1
    assert result.steps[0].verification_passed is False
