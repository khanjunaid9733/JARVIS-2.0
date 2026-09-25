from __future__ import annotations

"""Multimodal Cognition Package (Milestones M4 & M7.3, spec §92 / §93 / §131.7 / §24).

Provides:
- Voice Cognition:
  - `WhisperSTTAdapter`: Local / remote Whisper Speech-To-Text (`audio.transcribe`).
  - `PiperTTSAdapter`: Local / fast Piper Text-To-Speech (`audio.synthesize`).
- Visual Perception:
  - `VisionModelAdapter`: Local / remote vision models (`vision.describe`, `vision.analyze`).
- Real-Time Streaming & Continuous Pairing:
  - `StreamingVoiceLoop`: Event-driven voice turn-taking loop with barge-in support.
  - `VoiceTurnState`: Operational states of the voice interaction loop.
  - `ContinuousTutorSession`: Single-pipeline continuous voice-screen pairing session.
  - `ContinuousTutorState`: Lifecycle states of the continuous pairing tutor.
  - `TutorTurn`: Recorded multimodal interaction turn.
"""

from .continuous_tutor import (
    ContinuousTutorSession,
    ContinuousTutorState,
    TutorTurn,
)
from .streaming import StreamingVoiceLoop, VoiceTurnState
from .vision import VisionModelAdapter
from .voice import PiperTTSAdapter, WhisperSTTAdapter

__all__ = [
    "ContinuousTutorSession",
    "ContinuousTutorState",
    "PiperTTSAdapter",
    "StreamingVoiceLoop",
    "TutorTurn",
    "VisionModelAdapter",
    "VoiceTurnState",
    "WhisperSTTAdapter",
]
