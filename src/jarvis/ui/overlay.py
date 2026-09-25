"""Spatial Desktop HUD & Visual Guidance Overlay (Milestone M7.4).

Provides:
- CompanionStatus: Visual state of the floating companion pill (idle, listening, thinking, acting, emergency, blinded).
- VisualHighlight: Bounding box highlight with color, label, and coordinates.
- SpatialPointer: On-screen focal point directing human attention.
- SpatialOverlayEngine: Headless and native spatial guidance coordinator with instant E-Stop and Privacy Shutter controls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import enum
from typing import Any, Mapping, Optional, Sequence

from ..kernel.event_log import Event, EventLog, new_ulid
from ..perception.screen import ScreenBoundingBox, ScreenPrivacyShutter
from ..safety.estop import EStopLatch


class CompanionStatus(str, enum.Enum):
    """Visual operational status displayed on the floating HUD overlay."""

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    ACTING = "acting"
    EMERGENCY_STOPPED = "emergency_stopped"
    BLINDED = "blinded"


@dataclass(frozen=True)
class VisualHighlight:
    """A spatial highlight box rendered over a specific screen region."""

    highlight_id: str
    box: ScreenBoundingBox
    color: str = "#00FF88"  # Green default
    label: Optional[str] = None
    created_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )


@dataclass(frozen=True)
class SpatialPointer:
    """Spatial pointer directing creator attention to specific screen coordinates."""

    x: int
    y: int
    label: Optional[str] = None
    animated: bool = True


class SpatialOverlayEngine:
    """Coordinates on-screen spatial guidance, companion status HUD, and emergency aborts."""

    def __init__(
        self,
        event_log: Optional[EventLog] = None,
        estop_latch: Optional[EStopLatch] = None,
        privacy_shutter: Optional[ScreenPrivacyShutter] = None,
    ) -> None:
        self.log = event_log
        self.safety = estop_latch or EStopLatch(event_log=event_log)
        self.shutter = privacy_shutter or ScreenPrivacyShutter()

        self._status = CompanionStatus.IDLE
        self._highlights: dict[str, VisualHighlight] = {}
        self._active_pointer: Optional[SpatialPointer] = None
        self._visible: bool = True

    @property
    def status(self) -> CompanionStatus:
        if self.safety.is_tripped():
            return CompanionStatus.EMERGENCY_STOPPED
        if self.shutter.is_blinded:
            return CompanionStatus.BLINDED
        return self._status

    @property
    def is_visible(self) -> bool:
        return self._visible

    @property
    def active_highlights(self) -> list[VisualHighlight]:
        return list(self._highlights.values())

    @property
    def active_pointer(self) -> Optional[SpatialPointer]:
        return self._active_pointer

    def set_status(self, status: CompanionStatus) -> None:
        """Sets the active companion status."""
        self._status = status
        if self.log:
            try:
                self.log.append(
                    Event(
                        stream_id="ui.overlay",
                        event_type="overlay.status_changed",
                        principal_id="ui.spatial_overlay",
                        payload={"status": status.value},
                    )
                )
            except Exception:
                pass

    def add_highlight(
        self,
        box: ScreenBoundingBox,
        color: str = "#00FF88",
        label: Optional[str] = None,
    ) -> VisualHighlight:
        """Draws a visual highlight box around a target screen region."""
        hid = f"hl_{new_ulid()}"
        highlight = VisualHighlight(
            highlight_id=hid,
            box=box,
            color=color,
            label=label,
        )
        self._highlights[hid] = highlight

        if self.log:
            try:
                self.log.append(
                    Event(
                        stream_id="ui.overlay",
                        event_type="overlay.highlight_added",
                        principal_id="ui.spatial_overlay",
                        payload={
                            "highlight_id": hid,
                            "box": box.to_dict(),
                            "color": color,
                            "label": label,
                        },
                    )
                )
            except Exception:
                pass

        return highlight

    def remove_highlight(self, highlight_id: str) -> bool:
        """Removes a specific visual highlight."""
        if highlight_id in self._highlights:
            del self._highlights[highlight_id]
            return True
        return False

    def clear_highlights(self) -> None:
        """Clears all active screen highlights."""
        self._highlights.clear()
        if self.log:
            try:
                self.log.append(
                    Event(
                        stream_id="ui.overlay",
                        event_type="overlay.highlights_cleared",
                        principal_id="ui.spatial_overlay",
                        payload={},
                    )
                )
            except Exception:
                pass

    def point_to(self, x: int, y: int, label: Optional[str] = None) -> SpatialPointer:
        """Points an on-screen guidance indicator to specific coordinates."""
        pointer = SpatialPointer(x=x, y=y, label=label)
        self._active_pointer = pointer

        if self.log:
            try:
                self.log.append(
                    Event(
                        stream_id="ui.overlay",
                        event_type="overlay.pointer_moved",
                        principal_id="ui.spatial_overlay",
                        payload={"x": x, "y": y, "label": label},
                    )
                )
            except Exception:
                pass

        return pointer

    def clear_pointer(self) -> None:
        """Hides the active pointer."""
        self._active_pointer = None

    def trigger_emergency_stop(self, reason: str = "Creator clicked overlay Emergency Stop button") -> None:
        """Emergency Stop button: immediately halts all active automation."""
        self.safety.trip(reason=reason)
        self.clear_highlights()
        self.clear_pointer()
        self.set_status(CompanionStatus.EMERGENCY_STOPPED)

    def toggle_privacy_shutter(self, blind: Optional[bool] = None) -> bool:
        """Privacy Shutter button: toggles visual blinding."""
        should_blind = (not self.shutter.is_blinded) if blind is None else blind
        if should_blind:
            self.shutter.blind()
            self.clear_highlights()
            self.clear_pointer()
        else:
            self.shutter.unblind()
        return self.shutter.is_blinded
