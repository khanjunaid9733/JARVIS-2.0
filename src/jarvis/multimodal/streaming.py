from __future__ import annotations

"""Streaming Event Loop & Voice Turn-Taking FSM (Milestone M4, spec §92 / §93 / §119).

Provides:
1. `VoiceTurnState`: Explicit 6-state state machine for real-time voice interactions
   (`IDLE` -> `LISTENING` -> `USER_SPEAKING` -> `THINKING` -> `ASSISTANT_SPEAKING` / `INTERRUPTED`).
2. `StreamingVoiceLoop`: Event-driven coordinator managing:
   - Voice Activity Detection (VAD) audio frame streaming.
   - Low-latency turn-taking.
   - Barge-in / Interruption handling: User speaking while assistant is speaking immediately
     aborts audio playback and returns control to the user.
   - Structured event emission into `EventLog` or observer.

Invariants:
1. Low Latency: State transitions occur synchronously without blocking on model execution.
2. Barge-In Safety: Interruption cancels downstream audio synthesis/playback immediately.
3. Hermetic: No hard dependencies on ambient microphone drivers; frames are fed via
   `feed_audio_frame(frame: bytes, vad_active: bool)`.
"""

import enum
from typing import Any, Callable

from jarvis.kernel.event_log import Event, EventLog


class VoiceTurnState(str, enum.Enum):
    """Operational states of the voice turn-taking loop."""

    IDLE = "idle"                          # Awaiting wake word or activation
    LISTENING = "listening"                # Actively listening, VAD silent
    USER_SPEAKING = "user_speaking"        # VAD active, user is delivering speech
    THINKING = "thinking"                  # Speech ended, model is processing/generating
    ASSISTANT_SPEAKING = "assistant_speaking"  # TTS is rendering/playing audio response
    INTERRUPTED = "interrupted"            # User barged in during assistant playback


class StreamingVoiceLoop:
    """Real-time voice turn-taking event loop with barge-in support."""

    def __init__(
        self,
        *,
        event_log: EventLog | None = None,
        on_state_change: Callable[[VoiceTurnState, VoiceTurnState], None] | None = None,
        on_interrupted: Callable[[], None] | None = None,
        silence_threshold_frames: int = 5,
    ) -> None:
        self.event_log = event_log
        self._on_state_change = on_state_change
        self._on_interrupted = on_interrupted
        self.silence_threshold_frames = silence_threshold_frames

        self.state: VoiceTurnState = VoiceTurnState.IDLE
        self._consecutive_silence: int = 0
        self._audio_buffer: bytearray = bytearray()
        self._history: list[tuple[VoiceTurnState, str]] = []

    def _transition(self, new_state: VoiceTurnState, reason: str = "") -> None:
        old_state = self.state
        if old_state == new_state:
            return

        self.state = new_state
        self._history.append((new_state, reason))

        if self._on_state_change is not None:
            self._on_state_change(old_state, new_state)

        if self.event_log is not None:
            self.event_log.append(
                Event(
                    stream_id="voice-session",
                    event_type="multimodal.voice_state_changed",
                    principal_id="voice-loop",
                    payload={
                        "from_state": old_state.value,
                        "to_state": new_state.value,
                        "reason": reason,
                    },
                )
            )

    def start_listening(self) -> None:
        """Transitions state to LISTENING."""
        self._consecutive_silence = 0
        self._audio_buffer.clear()
        self._transition(VoiceTurnState.LISTENING, reason="start listening")

    def feed_audio_frame(self, frame: bytes, *, vad_active: bool) -> VoiceTurnState:
        """Feeds a chunk of audio with a VAD activity flag.

        Returns the resulting VoiceTurnState.
        """
        # 1. Barge-in / Interruption Check:
        # If assistant is speaking and user starts speaking, immediately interrupt!
        if self.state == VoiceTurnState.ASSISTANT_SPEAKING and vad_active:
            self._transition(VoiceTurnState.INTERRUPTED, reason="barge-in detected")
            if self._on_interrupted is not None:
                self._on_interrupted()
            self._audio_buffer.clear()
            self._audio_buffer.extend(frame)
            self._transition(VoiceTurnState.USER_SPEAKING, reason="user speaking after barge-in")
            return self.state

        # 2. In LISTENING or IDLE, user starts speaking
        if self.state in (VoiceTurnState.IDLE, VoiceTurnState.LISTENING):
            if vad_active:
                self._audio_buffer.clear()
                self._audio_buffer.extend(frame)
                self._consecutive_silence = 0
                self._transition(VoiceTurnState.USER_SPEAKING, reason="speech onset")
            return self.state

        # 3. In USER_SPEAKING
        if self.state == VoiceTurnState.USER_SPEAKING:
            self._audio_buffer.extend(frame)
            if vad_active:
                self._consecutive_silence = 0
            else:
                self._consecutive_silence += 1
                if self._consecutive_silence >= self.silence_threshold_frames:
                    # User finished speaking -> transition to THINKING
                    self._transition(VoiceTurnState.THINKING, reason="silence threshold reached")

        return self.state

    def start_assistant_speaking(self) -> None:
        """Called when assistant begins audio playback."""
        self._transition(VoiceTurnState.ASSISTANT_SPEAKING, reason="assistant playback started")

    def finish_assistant_speaking(self) -> None:
        """Called when assistant completes audio playback."""
        self._transition(VoiceTurnState.LISTENING, reason="assistant playback completed")

    def get_collected_audio(self) -> bytes:
        """Returns the accumulated user audio bytes from the current turn."""
        return bytes(self._audio_buffer)

    def reset(self) -> None:
        """Resets the loop to IDLE."""
        self._audio_buffer.clear()
        self._consecutive_silence = 0
        self._transition(VoiceTurnState.IDLE, reason="manual reset")


__all__ = [
    "StreamingVoiceLoop",
    "VoiceTurnState",
]
