"""Tests for Spatial Desktop HUD & Visual Guidance Overlay (Milestone M7.4)."""

from pathlib import Path
import pytest

from jarvis.kernel.event_log import EventLog
from jarvis.perception.screen import ScreenBoundingBox, ScreenPrivacyShutter
from jarvis.safety.estop import EStopLatch
from jarvis.ui.overlay import (
    CompanionStatus,
    SpatialOverlayEngine,
    SpatialPointer,
    VisualHighlight,
)


@pytest.fixture
def event_log(tmp_path: Path) -> EventLog:
    return EventLog(db_path=tmp_path / "test_overlay.db")


@pytest.fixture
def estop_latch(event_log: EventLog) -> EStopLatch:
    return EStopLatch(event_log=event_log)


@pytest.fixture
def privacy_shutter() -> ScreenPrivacyShutter:
    return ScreenPrivacyShutter()


def test_overlay_status_transitions(event_log: EventLog):
    engine = SpatialOverlayEngine(event_log=event_log)
    assert engine.status == CompanionStatus.IDLE

    engine.set_status(CompanionStatus.LISTENING)
    assert engine.status == CompanionStatus.LISTENING

    engine.set_status(CompanionStatus.THINKING)
    assert engine.status == CompanionStatus.THINKING

    engine.set_status(CompanionStatus.ACTING)
    assert engine.status == CompanionStatus.ACTING

    events = event_log.replay()
    assert len(events) == 3
    assert events[-1].payload["status"] == "acting"


def test_overlay_highlights_management(event_log: EventLog):
    engine = SpatialOverlayEngine(event_log=event_log)

    box = ScreenBoundingBox(x=100, y=150, width=200, height=50, label="deploy_button")
    hl = engine.add_highlight(box, color="#FF0055", label="Deploy Button")

    assert isinstance(hl, VisualHighlight)
    assert len(engine.active_highlights) == 1
    assert engine.active_highlights[0].box.x == 100
    assert engine.active_highlights[0].color == "#FF0055"

    # Remove specific highlight
    removed = engine.remove_highlight(hl.highlight_id)
    assert removed is True
    assert len(engine.active_highlights) == 0

    # Add multiple and clear
    engine.add_highlight(box)
    engine.add_highlight(ScreenBoundingBox(x=0, y=0, width=50, height=50))
    assert len(engine.active_highlights) == 2

    engine.clear_highlights()
    assert len(engine.active_highlights) == 0


def test_overlay_spatial_pointer(event_log: EventLog):
    engine = SpatialOverlayEngine(event_log=event_log)
    assert engine.active_pointer is None

    pointer = engine.point_to(x=500, y=300, label="Look here")
    assert isinstance(pointer, SpatialPointer)
    assert engine.active_pointer.x == 500
    assert engine.active_pointer.y == 300
    assert engine.active_pointer.label == "Look here"

    engine.clear_pointer()
    assert engine.active_pointer is None


def test_overlay_emergency_stop_button(
    event_log: EventLog,
    estop_latch: EStopLatch,
):
    engine = SpatialOverlayEngine(
        event_log=event_log,
        estop_latch=estop_latch,
    )

    box = ScreenBoundingBox(x=10, y=20, width=30, height=40)
    engine.add_highlight(box)
    engine.point_to(100, 100)

    # Click Emergency Stop
    engine.trigger_emergency_stop("Creator clicked emergency halt on overlay")

    assert estop_latch.is_tripped() is True
    assert engine.status == CompanionStatus.EMERGENCY_STOPPED
    assert len(engine.active_highlights) == 0
    assert engine.active_pointer is None


def test_overlay_privacy_shutter_button(
    event_log: EventLog,
    privacy_shutter: ScreenPrivacyShutter,
):
    engine = SpatialOverlayEngine(
        event_log=event_log,
        privacy_shutter=privacy_shutter,
    )

    box = ScreenBoundingBox(x=50, y=50, width=50, height=50)
    engine.add_highlight(box)
    engine.point_to(200, 200)

    # Toggle privacy shutter on
    is_blinded = engine.toggle_privacy_shutter()
    assert is_blinded is True
    assert privacy_shutter.is_blinded is True
    assert engine.status == CompanionStatus.BLINDED
    assert len(engine.active_highlights) == 0
    assert engine.active_pointer is None

    # Toggle privacy shutter off
    is_blinded = engine.toggle_privacy_shutter()
    assert is_blinded is False
    assert privacy_shutter.is_blinded is False
    assert engine.status == CompanionStatus.IDLE
