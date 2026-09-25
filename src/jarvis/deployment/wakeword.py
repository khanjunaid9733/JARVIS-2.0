from __future__ import annotations

"""Low-Power Perception & Hands-Free Wake-Word Seam (src/jarvis/deployment/wakeword.py).

Provides:
1. `WakeWordDetector` Protocol interface for external wake-word engines (openWakeWord, Porcupine, etc.)
2. `MockWakeWordDetector` for deterministic offline testing.
3. `WakeWordCoordinator` linking wake-word detection to M4's `StreamingVoiceLoop`.
4. Debounce refractory windows and audit event logging.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Any, Callable, Protocol, Sequence

from jarvis.kernel.event_log import Event, EventLog
from jarvis.multimodal.streaming import StreamingVoiceLoop, VoiceTurnState


@dataclass(frozen=True)
class WakeWordResult:
    """Detection result for an audio frame chunk."""

    detected: bool
    keyword: str = ""
    confidence: float = 0.0
    timestamp_utc: str = ""


class WakeWordDetector(Protocol):
    """Protocol for wake-word acoustic models."""

    @property
    def keywords(self) -> tuple[str, ...]: ...

    def process_audio(self, pcm_bytes: bytes) -> WakeWordResult: ...

    def reset(self) -> None: ...


class MockWakeWordDetector:
    """Deterministic scriptable wake-word detector for offline testing."""

    def __init__(
        self,
        keywords: Sequence[str] = ("hey_jarvis", "jarvis"),
        trigger_byte_pattern: bytes = b"WAKE",
        default_confidence: float = 0.95,
        confidence_threshold: float = 0.70,
    ) -> None:
        self._keywords = tuple(keywords)
        self.trigger_byte_pattern = trigger_byte_pattern
        self.default_confidence = default_confidence
        self.confidence_threshold = confidence_threshold
        self._manual_triggers: list[tuple[str, float]] = []

    @property
    def keywords(self) -> tuple[str, ...]:
        return self._keywords

    def queue_trigger(self, keyword: str = "hey_jarvis", confidence: float | None = None) -> None:
        """Queue a synthetic trigger for the next audio frame."""
        conf = confidence if confidence is not None else self.default_confidence
        self._manual_triggers.append((keyword, conf))

    def process_audio(self, pcm_bytes: bytes) -> WakeWordResult:
        now_iso = datetime.now(timezone.utc).isoformat()

        # Check manual queue
        if self._manual_triggers:
            kw, conf = self._manual_triggers.pop(0)
            if conf >= self.confidence_threshold:
                return WakeWordResult(
                    detected=True, keyword=kw, confidence=conf, timestamp_utc=now_iso
                )
            return WakeWordResult(
                detected=False, keyword=kw, confidence=conf, timestamp_utc=now_iso
            )

        # Check pattern in bytes
        if self.trigger_byte_pattern in pcm_bytes:
            return WakeWordResult(
                detected=True,
                keyword=self._keywords[0] if self._keywords else "jarvis",
                confidence=self.default_confidence,
                timestamp_utc=now_iso,
            )

        return WakeWordResult(detected=False, timestamp_utc=now_iso)

    def reset(self) -> None:
        self._manual_triggers.clear()


class WakeWordCoordinator:
    """Coordinates low-power wake-word detection and activates the streaming voice loop."""

    def __init__(
        self,
        detector: WakeWordDetector,
        voice_loop: StreamingVoiceLoop | None = None,
        event_log: EventLog | None = None,
        debounce_seconds: float = 1.0,
        on_wake: Callable[[WakeWordResult], None] | None = None,
    ) -> None:
        self.detector = detector
        self.voice_loop = voice_loop
        self.log = event_log
        self.debounce_seconds = debounce_seconds
        self.on_wake = on_wake

        self._last_detected_monotonic: float = 0.0
        self._detection_count: int = 0

    @property
    def detection_count(self) -> int:
        return self._detection_count

    def feed_audio(self, pcm_chunk: bytes) -> WakeWordResult:
        """Process incoming audio chunk and trigger voice loop if wake word matched."""
        result = self.detector.process_audio(pcm_chunk)
        now = time.monotonic()

        if result.detected:
            # Check debounce refractory window
            if now - self._last_detected_monotonic < self.debounce_seconds:
                return WakeWordResult(
                    detected=False,
                    keyword=result.keyword,
                    confidence=result.confidence,
                    timestamp_utc=result.timestamp_utc,
                )

            self._last_detected_monotonic = now
            self._detection_count += 1

            # Activate streaming voice loop if provided and IDLE
            if self.voice_loop and self.voice_loop.state == VoiceTurnState.IDLE:
                self.voice_loop.start_listening()

            if self.on_wake:
                try:
                    self.on_wake(result)
                except Exception:
                    pass

            if self.log:
                try:
                    self.log.append(
                        Event(
                            stream_id="voice",
                            event_type="wakeword.detected",
                            principal_id="wakeword_engine",
                            payload={
                                "keyword": result.keyword,
                                "confidence": result.confidence,
                                "timestamp": result.timestamp_utc,
                            },
                        )
                    )
                except Exception:
                    pass

        return result
