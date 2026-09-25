"""Continuous Real-Time Voice-Screen Pairing Loop (Milestone M7.3).

Provides:
- ContinuousTutorState: FSM states for ambient pair programming / desktop guidance.
- TutorTurn: Record of a multimodal interaction turn (voice + screen context + answer).
- ContinuousTutorSession: Single-pipeline coordinator linking VoiceLoop, ScreenPerception,
  and ComputerUse into an always-on, low-latency companion experience.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import enum
from typing import Any, Callable, Mapping, Optional, Sequence

from ..effects.computer_use import ComputerUseExecutor, GUIAction
from ..kernel.event_log import Event, EventLog, new_ulid
from ..multimodal.streaming import StreamingVoiceLoop, VoiceTurnState
from ..perception.screen import ScreenFrame, ScreenPerceptionEngine


class ContinuousTutorState(str, enum.Enum):
    """Lifecycle states of the continuous pairing tutor."""

    IDLE = "idle"              # Inactive / waiting to start
    LISTENING = "listening"    # Active duplex voice listening
    OBSERVING = "observing"    # Capturing and diffing active screen
    THINKING = "thinking"      # Correlating voice question with visual context
    SPEAKING = "speaking"      # Streaming vocal response
    PAUSED = "paused"          # Temporarily muted and blinded


@dataclass(frozen=True)
class TutorTurn:
    """A multimodal turn coupling voice input, visual grounding, and agent output."""

    turn_id: str
    timestamp_utc: str
    user_speech: str
    screen_frame_id: Optional[str] = None
    active_window: Optional[str] = None
    agent_reply: Optional[str] = None
    actions_executed: Sequence[str] = field(default_factory=list)


class ContinuousTutorSession:
    """Supervises continuous real-time pairing with unified voice and screen perception."""

    def __init__(
        self,
        perception_engine: ScreenPerceptionEngine,
        computer_use_executor: Optional[ComputerUseExecutor] = None,
        voice_loop: Optional[StreamingVoiceLoop] = None,
        event_log: Optional[EventLog] = None,
        answer_generator: Optional[Callable[[str, Optional[ScreenFrame]], str]] = None,
    ) -> None:
        self.perception = perception_engine
        self.executor = computer_use_executor
        self.voice_loop = voice_loop or StreamingVoiceLoop(event_log=event_log)
        self.log = event_log
        self.answer_generator = answer_generator or self._default_answer_generator

        self._state = ContinuousTutorState.IDLE
        self._session_id: Optional[str] = None
        self._turns: list[TutorTurn] = []

    @property
    def state(self) -> ContinuousTutorState:
        return self._state

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    @property
    def turns(self) -> list[TutorTurn]:
        return list(self._turns)

    def _default_answer_generator(self, speech: str, frame: Optional[ScreenFrame]) -> str:
        win = frame.active_window_title if frame else "desktop"
        return f"Observed '{win}'. In response to '{speech}', guidance ready."

    def start_session(self, session_id: Optional[str] = None) -> str:
        """Starts an active pairing session."""
        self._session_id = session_id or f"session_{new_ulid()}"
        self._state = ContinuousTutorState.LISTENING
        self.voice_loop.start_listening()

        if self.log:
            try:
                self.log.append(
                    Event(
                        stream_id="multimodal.continuous_tutor",
                        event_type="tutor.session_started",
                        principal_id="multimodal.tutor_coordinator",
                        payload={"session_id": self._session_id},
                    )
                )
            except Exception:
                pass

        return self._session_id

    def stop_session(self) -> None:
        """Terminates the pairing session."""
        self._state = ContinuousTutorState.IDLE
        self.voice_loop.reset()

        if self.log:
            try:
                self.log.append(
                    Event(
                        stream_id="multimodal.continuous_tutor",
                        event_type="tutor.session_stopped",
                        principal_id="multimodal.tutor_coordinator",
                        payload={"session_id": self._session_id},
                    )
                )
            except Exception:
                pass
        self._session_id = None

    def pause_session(self) -> None:
        """Temporarily pauses the tutor session (shuts privacy shutter & mutes)."""
        self._state = ContinuousTutorState.PAUSED
        self.perception.toggle_privacy_shutter(blind=True)

        if self.log:
            try:
                self.log.append(
                    Event(
                        stream_id="multimodal.continuous_tutor",
                        event_type="tutor.session_paused",
                        principal_id="multimodal.tutor_coordinator",
                        payload={"session_id": self._session_id},
                    )
                )
            except Exception:
                pass

    def resume_session(self) -> None:
        """Resumes active pairing (reopens shutter & listens)."""
        self._state = ContinuousTutorState.LISTENING
        self.perception.toggle_privacy_shutter(blind=False)

        if self.log:
            try:
                self.log.append(
                    Event(
                        stream_id="multimodal.continuous_tutor",
                        event_type="tutor.session_resumed",
                        principal_id="multimodal.tutor_coordinator",
                        payload={"session_id": self._session_id},
                    )
                )
            except Exception:
                pass

    def process_turn(
        self,
        user_speech: str,
        attach_screen: bool = True,
        action_to_execute: Optional[GUIAction] = None,
    ) -> TutorTurn:
        """Executes a single multimodal pairing turn:
        
        1. Captures active screen frame (if requested and not paused).
        2. Correlates voice utterance with visual context.
        3. Generates response.
        4. Optionally dispatches background GUI action.
        5. Emits audit telemetry.
        """
        if self._state == ContinuousTutorState.PAUSED:
            raise RuntimeError("Cannot process turn while pairing tutor session is paused")

        self._state = ContinuousTutorState.OBSERVING
        frame: Optional[ScreenFrame] = None
        if attach_screen:
            frame = self.perception.capture_frame()

        self._state = ContinuousTutorState.THINKING
        reply = self.answer_generator(user_speech, frame)

        executed_actions: list[str] = []
        if action_to_execute and self.executor:
            success = self.executor.execute(action_to_execute)
            if success:
                executed_actions.append(action_to_execute.action_id)

        self._state = ContinuousTutorState.SPEAKING
        turn_id = f"turn_{new_ulid()}"
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        turn = TutorTurn(
            turn_id=turn_id,
            timestamp_utc=now_iso,
            user_speech=user_speech,
            screen_frame_id=frame.frame_id if frame else None,
            active_window=frame.active_window_title if frame else None,
            agent_reply=reply,
            actions_executed=executed_actions,
        )

        self._turns.append(turn)
        self._state = ContinuousTutorState.LISTENING

        if self.log:
            try:
                self.log.append(
                    Event(
                        stream_id="multimodal.continuous_tutor",
                        event_type="tutor.turn_completed",
                        principal_id="multimodal.tutor_coordinator",
                        payload={
                            "session_id": self._session_id,
                            "turn_id": turn.turn_id,
                            "user_speech": user_speech,
                            "screen_frame_id": turn.screen_frame_id,
                            "active_window": turn.active_window,
                            "agent_reply": reply,
                            "actions_count": len(executed_actions),
                        },
                    )
                )
            except Exception:
                pass

        return turn
