"""Tests for Air-Gapped Screen Perception & Privacy Shutter (Milestone M7.1)."""

from pathlib import Path
import pytest

from jarvis.kernel.event_log import EventLog
from jarvis.perception.screen import (
    MockScreenGrabber,
    ScreenBoundingBox,
    ScreenDiffDetector,
    ScreenFrame,
    ScreenPerceptionEngine,
    ScreenPrivacyShutter,
)


@pytest.fixture
def mock_grabber() -> MockScreenGrabber:
    return MockScreenGrabber(
        width=1920,
        height=1080,
        initial_data=b"pixel_data_frame_one",
        active_window_title="Visual Studio Code - JARVIS2.0",
    )


@pytest.fixture
def event_log(tmp_path: Path) -> EventLog:
    return EventLog(db_path=tmp_path / "test_perception.db")


def test_screen_frame_capture_basic(mock_grabber: MockScreenGrabber):
    engine = ScreenPerceptionEngine(grabber=mock_grabber)
    frame = engine.capture_frame()

    assert isinstance(frame, ScreenFrame)
    assert frame.width == 1920
    assert frame.height == 1080
    assert frame.image_bytes == b"pixel_data_frame_one"
    assert frame.active_window_title == "Visual Studio Code - JARVIS2.0"
    assert frame.is_blinded is False
    assert len(frame.dhash) == 64


def test_screen_diff_detector_identical_vs_changed(mock_grabber: MockScreenGrabber):
    engine = ScreenPerceptionEngine(grabber=mock_grabber)
    f1 = engine.capture_frame()

    # Second capture with identical content
    f2 = engine.capture_frame()
    has_changed, dirty = engine.diff_detector.detect_diff(f2, f1)
    assert has_changed is False
    assert len(dirty) == 0

    # Modify mock content
    mock_grabber.set_frame_content(b"pixel_data_frame_two_changed")
    f3 = engine.capture_frame()
    has_changed, dirty = engine.diff_detector.detect_diff(f3, f2)
    assert has_changed is True
    assert len(dirty) > 0


def test_screen_privacy_shutter_blind_and_unblind(mock_grabber: MockScreenGrabber):
    engine = ScreenPerceptionEngine(grabber=mock_grabber)

    # Initial capture is unblinded
    f1 = engine.capture_frame()
    assert f1.is_blinded is False
    assert f1.image_bytes == b"pixel_data_frame_one"

    # Close privacy shutter
    engine.toggle_privacy_shutter(blind=True)
    assert engine.shutter.is_blinded is True

    f2 = engine.capture_frame()
    assert f2.is_blinded is True
    assert f2.image_bytes == b"\x00" * len(b"pixel_data_frame_one")
    assert f2.dhash.startswith("blinded_")
    assert len(f2.redacted_regions) > 0

    # Re-open privacy shutter
    engine.toggle_privacy_shutter(blind=False)
    assert engine.shutter.is_blinded is False

    f3 = engine.capture_frame()
    assert f3.is_blinded is False
    assert f3.image_bytes == b"pixel_data_frame_one"


def test_screen_privacy_shutter_sensitive_redaction(mock_grabber: MockScreenGrabber):
    engine = ScreenPerceptionEngine(grabber=mock_grabber)
    sensitive_box = ScreenBoundingBox(x=100, y=200, width=300, height=50, label="api_key_field")

    frame = engine.capture_frame(sensitive_regions=[sensitive_box])
    assert frame.pii_redacted is True
    assert len(frame.redacted_regions) == 1
    assert frame.redacted_regions[0].label == "api_key_field"


def test_screen_perception_engine_emits_audit_events(
    mock_grabber: MockScreenGrabber,
    event_log: EventLog,
):
    engine = ScreenPerceptionEngine(grabber=mock_grabber, event_log=event_log)

    engine.capture_frame()
    engine.toggle_privacy_shutter(blind=True)
    engine.capture_frame()

    events = event_log.replay()
    event_types = [e.event_type for e in events]

    assert "perception.screen_captured" in event_types
    assert "perception.privacy_shutter_toggled" in event_types
    assert len(events) == 3


def test_screen_window_capture(mock_grabber: MockScreenGrabber):
    frame = mock_grabber.capture_window("Visual Studio Code")
    assert frame is not None
    assert frame.active_window_title == "Visual Studio Code - JARVIS2.0"

    missing = mock_grabber.capture_window("NonExistentWindow")
    assert missing is None
