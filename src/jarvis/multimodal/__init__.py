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
- Real-Time Voice Assistant (additive, Phase A/B):
  - `JarvisVoiceAssistant`: Complete mic → VAD → STT → LLM → TTS → speaker loop.
  - `NeuralTTSEngine`: Edge TTS neural voice with pyttsx3 fallback.
  - `RealMicrophone`: Live microphone capture with energy-based VAD.
  - `RealSpeaker`: Non-blocking WAV speaker playback with barge-in support.
"""

from .continuous_tutor import (
    ContinuousTutorSession,
    ContinuousTutorState,
    TutorTurn,
)
from .streaming import StreamingVoiceLoop, VoiceTurnState
from .vision import VisionModelAdapter
from .voice import PiperTTSAdapter, WhisperSTTAdapter

# Lazy imports for the new real-time pipeline (avoid hard dependency at package import)
def __getattr__(name: str):  # type: ignore[override]
    if name == "JarvisVoiceAssistant":
        from .jarvis_voice import JarvisVoiceAssistant
        return JarvisVoiceAssistant
    if name == "NeuralTTSEngine":
        from .neural_tts import NeuralTTSEngine
        return NeuralTTSEngine
    if name == "RealMicrophone":
        from .audio_io import RealMicrophone
        return RealMicrophone
    if name == "RealSpeaker":
        from .audio_io import RealSpeaker
        return RealSpeaker
    if name == "SkillCreator":
        from .skill_creator import SkillCreator
        return SkillCreator
    if name == "SkillCreationResult":
        from .skill_creator import SkillCreationResult
        return SkillCreationResult
    if name == "is_skill_creation_intent":
        from .skill_creator import is_skill_creation_intent
        return is_skill_creation_intent
    if name == "sanitize_skill_name":
        from .skill_creator import sanitize_skill_name
        return sanitize_skill_name
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ContinuousTutorSession",
    "ContinuousTutorState",
    "JarvisVoiceAssistant",
    "NeuralTTSEngine",
    "PiperTTSAdapter",
    "RealMicrophone",
    "RealSpeaker",
    "SkillCreationResult",
    "SkillCreator",
    "StreamingVoiceLoop",
    "TutorTurn",
    "VisionModelAdapter",
    "VoiceTurnState",
    "WhisperSTTAdapter",
    "is_skill_creation_intent",
    "sanitize_skill_name",
]
