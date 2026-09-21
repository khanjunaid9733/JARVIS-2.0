from __future__ import annotations

"""Multimodal Cognition Package (Milestone M4, spec §92 / §93 / §131.7 / §131.13).

Provides:
- Voice Cognition:
  - `WhisperSTTAdapter`: Local / remote Whisper Speech-To-Text (`audio.transcribe`).
  - `PiperTTSAdapter`: Local / fast Piper Text-To-Speech (`audio.synthesize`).
- Visual Perception:
  - `VisionModelAdapter`: Local / remote vision models (`vision.describe`, `vision.analyze`).
- Real-Time Streaming:
  - `StreamingVoiceLoop`: Event-driven voice turn-taking loop with barge-in support.
  - `VoiceTurnState`: Operational states of the voice interaction loop.
"""

from .streaming import StreamingVoiceLoop, VoiceTurnState
from .vision import VisionModelAdapter
from .voice import PiperTTSAdapter, WhisperSTTAdapter

__all__ = [
    "PiperTTSAdapter",
    "StreamingVoiceLoop",
    "VisionModelAdapter",
    "VoiceTurnState",
    "WhisperSTTAdapter",
]
