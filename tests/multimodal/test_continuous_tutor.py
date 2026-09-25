"""Tests for Continuous Real-Time Voice-Screen Pairing Loop (Milestone M7.3)."""

from pathlib import Path
import pytest

from jarvis.effects.computer_use import (
    ComputerUseExecutor,
    DeliveryMode,
    GUIAction,
    GUIActionType,
    MockComputerUseDriver,
)
from jarvis.kernel.event_log import EventLog
from jarvis.multimodal.continuous_tutor import (
    ContinuousTutorSession,
    ContinuousTutorState,
    TutorTurn,
)
from jarvis.perception.screen import (
    MockScreenGrabber,
    ScreenPerceptionEngine,
)


@pytest.fixture
def mock_grabber() -> MockScreenGrabber:
    return MockScreenGrabber(
        width=1920,
        height=1080,
        initial_data=b"mock_desktop_editor_content",
        active_window_title="Editor - main.py",
    )


@pytest.fixture
def perception_engine(mock_grabber: MockScreenGrabber) -> ScreenPerceptionEngine:
    return ScreenPerceptionEngine(grabber=mock_grabber)


@pytest.fixture
def mock_driver() -> MockComputerUseDriver:
    return MockComputerUseDriver()


@pytest.fixture
def computer_use_executor(mock_driver: MockComputerUseDriver) -> ComputerUseExecutor:
    return ComputerUseExecutor(driver=mock_driver)


@pytest.fixture
def event_log(tmp_path: Path) -> EventLog:
    return EventLog(db_path=tmp_path / "test_tutor.db")


def test_tutor_session_start_and_stop(
    perception_engine: ScreenPerceptionEngine,
    computer_use_executor: ComputerUseExecutor,
    event_log: EventLog,
):
    session = ContinuousTutorSession(
        perception_engine=perception_engine,
        computer_use_executor=computer_use_executor,
        event_log=event_log,
    )

    assert session.state == ContinuousTutorState.IDLE
    sid = session.start_session("custom_session_1")
    assert sid == "custom_session_1"
    assert session.state == ContinuousTutorState.LISTENING

    session.stop_session()
    assert session.state == ContinuousTutorState.IDLE
    assert session.session_id is None

    events = event_log.replay()
    types = [e.event_type for e in events]
    assert "tutor.session_started" in types
    assert "tutor.session_stopped" in types


def test_tutor_turn_with_screen_context(
    perception_engine: ScreenPerceptionEngine,
    computer_use_executor: ComputerUseExecutor,
    event_log: EventLog,
):
    session = ContinuousTutorSession(
        perception_engine=perception_engine,
        computer_use_executor=computer_use_executor,
        event_log=event_log,
    )
    session.start_session()

    turn = session.process_turn(
        user_speech="What is on my screen?",
        attach_screen=True,
    )

    assert isinstance(turn, TutorTurn)
    assert turn.user_speech == "What is on my screen?"
    assert turn.active_window == "Editor - main.py"
    assert turn.screen_frame_id is not None
    assert "Editor - main.py" in turn.agent_reply

    assert len(session.turns) == 1
    events = event_log.replay()
    types = [e.event_type for e in events]
    assert "tutor.turn_completed" in types


def test_tutor_turn_executes_gui_action(
    perception_engine: ScreenPerceptionEngine,
    mock_driver: MockComputerUseDriver,
    computer_use_executor: ComputerUseExecutor,
):
    session = ContinuousTutorSession(
        perception_engine=perception_engine,
        computer_use_executor=computer_use_executor,
    )
    session.start_session()

    click_action = GUIAction(
        action_type=GUIActionType.CLICK,
        delivery_mode=DeliveryMode.BACKGROUND_HEADLESS,
        coordinates=(400, 300),
    )

    turn = session.process_turn(
        user_speech="Click the run button",
        action_to_execute=click_action,
    )

    assert len(turn.actions_executed) == 1
    assert turn.actions_executed[0] == click_action.action_id
    assert len(mock_driver.executed_actions) == 1


def test_tutor_pause_and_resume_privacy_shutter(
    perception_engine: ScreenPerceptionEngine,
    computer_use_executor: ComputerUseExecutor,
):
    session = ContinuousTutorSession(
        perception_engine=perception_engine,
        computer_use_executor=computer_use_executor,
    )
    session.start_session()

    # Pause session: shutter closes
    session.pause_session()
    assert session.state == ContinuousTutorState.PAUSED
    assert perception_engine.shutter.is_blinded is True

    # Processing turn while paused must fail
    with pytest.raises(RuntimeError):
        session.process_turn("Hello")

    # Resume session: shutter opens
    session.resume_session()
    assert session.state == ContinuousTutorState.LISTENING
    assert perception_engine.shutter.is_blinded is False

    turn = session.process_turn("Hello now")
    assert turn is not None
