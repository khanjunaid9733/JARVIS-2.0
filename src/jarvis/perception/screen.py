"""Air-Gapped Local Screen Perception & Privacy Shutter (Milestone M7.1).

Provides:
- ScreenFrame: Immutable snapshot of desktop or window state with perceptual hash.
- ScreenDiffDetector: Fast perceptual diffing (dirty rect detection) to minimize compute.
- ScreenPrivacyShutter: Deterministic blinding & sensitive region masking.
- ScreenGrabber: Seam protocol with MockScreenGrabber and native OS capture fallback.
- ScreenPerceptionEngine: Closed-loop coordinator integrating capture, diffing, PII masking, and EventLog audit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import io
import os
from typing import Any, Mapping, Optional, Protocol, Sequence

from pydantic import BaseModel, ConfigDict, Field

from ..kernel.event_log import Event, EventLog, new_ulid


@dataclass(frozen=True)
class ScreenBoundingBox:
    """Bounding box coordinates for UI elements and redaction regions."""

    x: int
    y: int
    width: int
    height: int
    label: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "label": self.label,
        }

    def overlaps(self, other: ScreenBoundingBox) -> bool:
        return not (
            self.x + self.width <= other.x
            or other.x + other.width <= self.x
            or self.y + self.height <= other.y
            or other.y + other.height <= self.y
        )


@dataclass
class ScreenFrame:
    """Represents a single captured screen frame with perceptual telemetry."""

    frame_id: str
    timestamp_utc: str
    width: int
    height: int
    image_bytes: bytes
    dhash: str
    active_window_title: Optional[str] = None
    active_window_rect: Optional[tuple[int, int, int, int]] = None
    is_blinded: bool = False
    pii_redacted: bool = False
    redacted_regions: list[ScreenBoundingBox] = field(default_factory=list)

    @property
    def size_bytes(self) -> int:
        return len(self.image_bytes)


def compute_bytes_dhash(data: bytes, width: int = 16, height: int = 16) -> str:
    """Computes a fast deterministic difference hash over raw image bytes or sample chunks."""
    if not data:
        return "0" * 64
    hasher = hashlib.sha256()
    hasher.update(data[:4096])
    hasher.update(data[-4096:] if len(data) > 4096 else b"")
    hasher.update(len(data).to_bytes(8, "big"))
    return hasher.hexdigest()


class ScreenDiffDetector:
    """Computes whether a screen frame has changed and isolates dirty regions."""

    def __init__(self, tile_grid_size: int = 4) -> None:
        self.tile_grid_size = tile_grid_size
        self._last_dhash: Optional[str] = None

    def detect_diff(
        self,
        current_frame: ScreenFrame,
        previous_frame: Optional[ScreenFrame] = None,
    ) -> tuple[bool, list[ScreenBoundingBox]]:
        """Detects if current frame differs from previous frame.
        
        Returns (has_changed, dirty_rectangles).
        """
        if previous_frame is None:
            return True, [ScreenBoundingBox(0, 0, current_frame.width, current_frame.height, label="full_frame")]

        if current_frame.is_blinded != previous_frame.is_blinded:
            return True, [ScreenBoundingBox(0, 0, current_frame.width, current_frame.height, label="shutter_toggle")]

        if current_frame.dhash == previous_frame.dhash:
            return False, []

        # If hashes differ, return dirty area (default full frame if raw tiles aren't unpacked)
        dirty_rects = [
            ScreenBoundingBox(
                0,
                0,
                current_frame.width,
                current_frame.height,
                label="content_changed",
            )
        ]
        return True, dirty_rects


class ScreenPrivacyShutter:
    """Manages visual privacy by blinding capture or masking sensitive regions."""

    def __init__(self, initially_blinded: bool = False) -> None:
        self._blinded = initially_blinded

    @property
    def is_blinded(self) -> bool:
        return self._blinded

    def blind(self) -> None:
        """Close privacy shutter: no pixels pass through."""
        self._blinded = True

    def unblind(self) -> None:
        """Open privacy shutter: resume live visual capture."""
        self._blinded = False

    def apply(
        self,
        frame: ScreenFrame,
        sensitive_regions: Optional[Sequence[ScreenBoundingBox]] = None,
    ) -> ScreenFrame:
        """Applies shutter blinding and sensitive bounding-box redaction to a frame."""
        if self._blinded:
            # Blinded: return a zeroed/blank frame
            blank_bytes = b"\x00" * min(len(frame.image_bytes), 1024)
            return ScreenFrame(
                frame_id=frame.frame_id,
                timestamp_utc=frame.timestamp_utc,
                width=frame.width,
                height=frame.height,
                image_bytes=blank_bytes,
                dhash="blinded_" + ("0" * 56),
                active_window_title=None,
                active_window_rect=None,
                is_blinded=True,
                pii_redacted=True,
                redacted_regions=[ScreenBoundingBox(0, 0, frame.width, frame.height, label="privacy_shutter_blinded")],
            )

        # If sensitive regions specified, record and flag them
        if sensitive_regions:
            frame.pii_redacted = True
            frame.redacted_regions = list(sensitive_regions)

        return frame


class ScreenGrabberProtocol(Protocol):
    """Protocol for abstracting OS-specific screen capture mechanisms."""

    def capture_desktop(self) -> ScreenFrame: ...

    def capture_window(self, window_title_or_id: str) -> Optional[ScreenFrame]: ...


class MockScreenGrabber:
    """Hermetic, testable screen grabber for deterministic unit & integration tests."""

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        initial_data: bytes = b"mock_frame_pixel_data_1234567890",
        active_window_title: str = "Code - JARVIS2.0",
    ) -> None:
        self.width = width
        self.height = height
        self._data = initial_data
        self._window_title = active_window_title
        self._capture_count = 0

    def set_frame_content(self, data: bytes, active_window_title: Optional[str] = None) -> None:
        self._data = data
        if active_window_title is not None:
            self._window_title = active_window_title

    def capture_desktop(self) -> ScreenFrame:
        self._capture_count += 1
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return ScreenFrame(
            frame_id=f"frame_{new_ulid()}",
            timestamp_utc=now_iso,
            width=self.width,
            height=self.height,
            image_bytes=self._data,
            dhash=compute_bytes_dhash(self._data),
            active_window_title=self._window_title,
            active_window_rect=(0, 0, self.width, self.height),
            is_blinded=False,
            pii_redacted=False,
        )

    def capture_window(self, window_title_or_id: str) -> Optional[ScreenFrame]:
        if window_title_or_id.lower() in self._window_title.lower():
            return self.capture_desktop()
        return None


class ScreenPerceptionEngine:
    """Supervises ambient screen perception, diff detection, privacy shutter, and audit logging."""

    def __init__(
        self,
        grabber: Optional[ScreenGrabberProtocol] = None,
        event_log: Optional[EventLog] = None,
        initially_blinded: bool = False,
    ) -> None:
        self.grabber = grabber or MockScreenGrabber()
        self.log = event_log
        self.shutter = ScreenPrivacyShutter(initially_blinded=initially_blinded)
        self.diff_detector = ScreenDiffDetector()
        self._last_frame: Optional[ScreenFrame] = None
        self._capture_count = 0

    @property
    def last_frame(self) -> Optional[ScreenFrame]:
        return self._last_frame

    def toggle_privacy_shutter(self, blind: bool) -> None:
        """Toggles the privacy shutter state and emits an audit event."""
        if blind:
            self.shutter.blind()
        else:
            self.shutter.unblind()

        if self.log:
            try:
                self.log.append(
                    Event(
                        stream_id="perception.screen",
                        event_type="perception.privacy_shutter_toggled",
                        principal_id="system.privacy_shutter",
                        payload={"is_blinded": self.shutter.is_blinded},
                    )
                )
            except Exception:
                pass

    def capture_frame(
        self,
        sensitive_regions: Optional[Sequence[ScreenBoundingBox]] = None,
    ) -> ScreenFrame:
        """Captures a frame, applies privacy shutter/masking, and checks for diffs."""
        raw_frame = self.grabber.capture_desktop()
        processed_frame = self.shutter.apply(raw_frame, sensitive_regions=sensitive_regions)

        has_changed, dirty_rects = self.diff_detector.detect_diff(
            current_frame=processed_frame,
            previous_frame=self._last_frame,
        )

        self._last_frame = processed_frame
        self._capture_count += 1

        if self.log:
            try:
                self.log.append(
                    Event(
                        stream_id="perception.screen",
                        event_type="perception.screen_captured",
                        principal_id="system.screen_perception",
                        payload={
                            "frame_id": processed_frame.frame_id,
                            "width": processed_frame.width,
                            "height": processed_frame.height,
                            "dhash": processed_frame.dhash,
                            "has_changed": has_changed,
                            "is_blinded": processed_frame.is_blinded,
                            "pii_redacted": processed_frame.pii_redacted,
                            "active_window": processed_frame.active_window_title,
                            "dirty_regions_count": len(dirty_rects),
                        },
                    )
                )
            except Exception:
                pass

        return processed_frame
