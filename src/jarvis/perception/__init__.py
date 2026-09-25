"""Screen perception and multimodal visual grounding package for JARVIS 2.0."""

from __future__ import annotations

from .screen import (
    MockScreenGrabber,
    ScreenBoundingBox,
    ScreenDiffDetector,
    ScreenFrame,
    ScreenGrabberProtocol,
    ScreenPerceptionEngine,
    ScreenPrivacyShutter,
    compute_bytes_dhash,
)

__all__ = [
    "MockScreenGrabber",
    "ScreenBoundingBox",
    "ScreenDiffDetector",
    "ScreenFrame",
    "ScreenGrabberProtocol",
    "ScreenPerceptionEngine",
    "ScreenPrivacyShutter",
    "compute_bytes_dhash",
]
