"""Tests for the real-time voice assistant pipeline (Phase A/B).

Tests audio_io, neural_tts, and jarvis_voice modules without requiring
live hardware (uses mock drivers and seams throughout).
"""

from __future__ import annotations

import io
import struct
import wave
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# audio_io tests
# ---------------------------------------------------------------------------


class TestMockMicrophone:
    """Tests for the MockMicrophone driver."""

    def test_mock_microphone_starts_and_stops(self):
        from jarvis.multimodal.audio_io import MockMicrophone

        mic = MockMicrophone()
        assert not mic.is_active
        mic.start()
        assert mic.is_active
        mic.stop()
        assert not mic.is_active

    def test_mock_microphone_reads_queued_frames(self):
        from jarvis.multimodal.audio_io import MockMicrophone

        mic = MockMicrophone()
        mic.enqueue_frames([
            (b"\x00" * 100, False),  # silence
            (b"\xff" * 100, True),   # speech
        ])
        mic.start()

        frame1 = mic.read_frame()
        assert frame1 is not None
        assert not frame1.is_speech
        assert frame1.frame_index == 0

        frame2 = mic.read_frame()
        assert frame2 is not None
        assert frame2.is_speech
        assert frame2.frame_index == 1

        # No more frames
        assert mic.read_frame() is None

    def test_mock_microphone_returns_none_when_inactive(self):
        from jarvis.multimodal.audio_io import MockMicrophone

        mic = MockMicrophone()
        mic.enqueue_frames([(b"\x00" * 100, False)])
        # Not started — should return None
        assert mic.read_frame() is None

    def test_mock_microphone_sample_rate_and_frame_size(self):
        from jarvis.multimodal.audio_io import MockMicrophone

        mic = MockMicrophone(sample_rate=16000, frame_duration_ms=30)
        assert mic.sample_rate == 16000
        assert mic.frame_size == 480  # 16000 * 30 / 1000


class TestMockSpeaker:
    """Tests for the MockSpeaker driver."""

    def test_mock_speaker_plays_and_records(self):
        from jarvis.multimodal.audio_io import MockSpeaker

        spk = MockSpeaker()
        assert not spk.is_playing
        spk.play_wav(b"fake_wav_data")
        assert len(spk.played_audio) == 1
        assert spk.played_audio[0] == b"fake_wav_data"

    def test_mock_speaker_stops_playback(self):
        from jarvis.multimodal.audio_io import MockSpeaker

        spk = MockSpeaker()
        spk._playing = True
        spk.stop_playback()
        assert not spk.is_playing


class TestAudioDeviceInfo:
    """Tests for audio device discovery."""

    def test_audio_device_info_fields(self):
        from jarvis.multimodal.audio_io import AudioDeviceInfo

        device = AudioDeviceInfo(
            index=0, name="Test Mic", max_input_channels=2,
            max_output_channels=0, default_sample_rate=44100.0,
            is_input=True, is_output=False,
        )
        assert device.name == "Test Mic"
        assert device.is_input
        assert not device.is_output

    def test_list_audio_devices_returns_list(self):
        from jarvis.multimodal.audio_io import list_audio_devices

        # Should return a list even if pyaudio fails
        result = list_audio_devices()
        assert isinstance(result, list)


class TestAudioFrame:
    """Tests for AudioFrame dataclass."""

    def test_audio_frame_is_immutable(self):
        from jarvis.multimodal.audio_io import AudioFrame

        frame = AudioFrame(
            data=b"\x00" * 100, rms_energy=0.05,
            is_speech=True, timestamp=1234.5, frame_index=0,
        )
        assert frame.is_speech
        assert frame.rms_energy == 0.05
        with pytest.raises(AttributeError):
            frame.data = b"\xff"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# neural_tts tests
# ---------------------------------------------------------------------------


class TestNeuralTTSEngine:
    """Tests for NeuralTTSEngine."""

    def test_engine_init_with_defaults(self):
        from jarvis.multimodal.neural_tts import NeuralTTSEngine, DEFAULT_VOICE

        engine = NeuralTTSEngine()
        assert engine.voice == DEFAULT_VOICE
        assert engine.prefer_edge is True

    def test_engine_rejects_empty_text(self):
        from jarvis.multimodal.neural_tts import NeuralTTSEngine

        engine = NeuralTTSEngine()
        with pytest.raises(ValueError, match="empty"):
            engine.synthesize("")

    def test_engine_rejects_whitespace_only(self):
        from jarvis.multimodal.neural_tts import NeuralTTSEngine

        engine = NeuralTTSEngine()
        with pytest.raises(ValueError, match="empty"):
            engine.synthesize("   ")

    def test_make_runner_returns_callable(self):
        from jarvis.multimodal.neural_tts import NeuralTTSEngine

        engine = NeuralTTSEngine()
        runner = engine.make_runner()
        assert callable(runner)

    def test_measure_wav_detects_silence(self):
        from jarvis.multimodal.neural_tts import _measure_wav

        # Create a silent WAV
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00\x00" * 1000)  # 1000 silent samples
        silent_wav = buf.getvalue()

        facts = _measure_wav(silent_wav)
        assert facts["peak"] == 0.0
        assert not facts["non_silent"]

    def test_measure_wav_detects_speech(self):
        from jarvis.multimodal.neural_tts import _measure_wav

        # Create a WAV with content
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            # Sine-wave-ish samples
            samples = [int(10000 * ((-1) ** i)) for i in range(2000)]
            wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        speech_wav = buf.getvalue()

        facts = _measure_wav(speech_wav)
        assert facts["peak"] > 0.1
        assert facts["non_silent"]

    def test_edge_voices_dict_has_jarvis(self):
        from jarvis.multimodal.neural_tts import EDGE_VOICES

        assert "jarvis" in EDGE_VOICES
        assert "jarvis_uk" in EDGE_VOICES


# ---------------------------------------------------------------------------
# jarvis_voice tests
# ---------------------------------------------------------------------------


class TestConversationMemory:
    """Tests for multi-turn conversation memory."""

    def test_add_and_retrieve(self):
        from jarvis.multimodal.jarvis_voice import ConversationMemory

        mem = ConversationMemory()
        mem.add("user", "Hello JARVIS")
        mem.add("assistant", "Good day, sir.")

        messages = mem.get_messages()
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"
        assert mem.turn_count == 2

    def test_max_turns_trimming(self):
        from jarvis.multimodal.jarvis_voice import ConversationMemory

        mem = ConversationMemory(max_turns=3)
        for i in range(10):
            mem.add("user", f"message {i}")

        assert mem.turn_count == 3
        messages = mem.get_messages()
        # System + 3 turns
        assert len(messages) == 4

    def test_clear(self):
        from jarvis.multimodal.jarvis_voice import ConversationMemory

        mem = ConversationMemory()
        mem.add("user", "test")
        mem.clear()
        assert mem.turn_count == 0

    def test_system_prompt_included(self):
        from jarvis.multimodal.jarvis_voice import ConversationMemory, JARVIS_SYSTEM_PROMPT

        mem = ConversationMemory()
        messages = mem.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert "JARVIS" in messages[0]["content"]


class TestLLMEngine:
    """Tests for LLM engine auto-detection and offline fallback."""

    def test_offline_fallback_greeting(self):
        from jarvis.multimodal.jarvis_voice import LLMEngine

        engine = LLMEngine(provider="offline")
        engine._resolved_provider = "offline"
        result = engine._offline_response([
            {"role": "system", "content": "You are JARVIS."},
            {"role": "user", "content": "hello"},
        ])
        assert "sir" in result.lower() or "assist" in result.lower() or "day" in result.lower()

    def test_offline_fallback_time(self):
        from jarvis.multimodal.jarvis_voice import LLMEngine

        engine = LLMEngine(provider="offline")
        result = engine._offline_response([
            {"role": "user", "content": "what time is it"},
        ])
        assert "time" in result.lower()

    def test_offline_fallback_date(self):
        from jarvis.multimodal.jarvis_voice import LLMEngine

        engine = LLMEngine(provider="offline")
        result = engine._offline_response([
            {"role": "user", "content": "what day is today"},
        ])
        assert any(day in result.lower() for day in [
            "monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday",
        ])

    def test_offline_fallback_unknown(self):
        from jarvis.multimodal.jarvis_voice import LLMEngine

        engine = LLMEngine(provider="offline")
        result = engine._offline_response([
            {"role": "user", "content": "explain quantum computing in detail"},
        ])
        assert "offline" in result.lower()


class TestSTTEngine:
    """Tests for STT engine initialization."""

    def test_stt_engine_creates_recognizer(self):
        from jarvis.multimodal.jarvis_voice import STTEngine

        stt = STTEngine(model="tiny")
        assert stt.model == "tiny"
        rec = stt._get_recognizer()
        assert rec is not None


class TestJarvisVoiceAssistant:
    """Tests for the main assistant (without hardware)."""

    def test_assistant_constructs(self):
        from jarvis.multimodal.jarvis_voice import JarvisVoiceAssistant

        assistant = JarvisVoiceAssistant(greeting=False, verbose=False)
        assert not assistant._running
        assert assistant._turn_count == 0

    def test_single_turn_offline(self):
        from jarvis.multimodal.jarvis_voice import JarvisVoiceAssistant

        assistant = JarvisVoiceAssistant(
            llm_provider="offline", greeting=False, verbose=False,
        )
        # Override the LLM to force offline
        assistant.llm._resolved_provider = "offline"
        assistant.llm._client = None

        response = assistant.single_turn("hello")
        assert response  # Should produce something
        assert len(response) > 0

    def test_stop_sets_running_false(self):
        from jarvis.multimodal.jarvis_voice import JarvisVoiceAssistant

        assistant = JarvisVoiceAssistant(greeting=False, verbose=False)
        assistant._running = True
        assistant.stop()
        assert not assistant._running


class TestJarvisPersona:
    """Tests for the JARVIS persona constants."""

    def test_system_prompt_contains_jarvis(self):
        from jarvis.multimodal.jarvis_voice import JARVIS_SYSTEM_PROMPT

        assert "JARVIS" in JARVIS_SYSTEM_PROMPT
        assert "Just A Rather Very Intelligent System" in JARVIS_SYSTEM_PROMPT

    def test_greeting_is_warm(self):
        from jarvis.multimodal.jarvis_voice import JARVIS_GREETING

        assert "sir" in JARVIS_GREETING.lower()
        assert "JARVIS" in JARVIS_GREETING


# ---------------------------------------------------------------------------
# Skill Creator tests
# ---------------------------------------------------------------------------


class TestSkillCreator:
    """Tests for autonomous skill creation and voice command dispatch."""

    def test_sanitize_skill_name(self):
        from jarvis.multimodal.skill_creator import sanitize_skill_name

        assert sanitize_skill_name("create a new skill for automated git commits") == "automated-git-commits"
        assert sanitize_skill_name("build a skill to play music and songs") == "play-music-and-songs"
        assert sanitize_skill_name("make a new skill called system-health-checker") == "system-health-checker"
        assert sanitize_skill_name("!@#$") == "custom-skill"
        assert sanitize_skill_name("") == "custom-skill"

    def test_is_skill_creation_intent(self):
        from jarvis.multimodal.skill_creator import is_skill_creation_intent

        assert is_skill_creation_intent("Jarvis create a new skill to manage docker containers")
        assert is_skill_creation_intent("Please make a skill for reading pdf documents")
        assert is_skill_creation_intent("Can you build that capability as a skill")
        assert is_skill_creation_intent("write a new skill for crypto trading alerts")
        assert not is_skill_creation_intent("What is the weather in Tokyo right now?")
        assert not is_skill_creation_intent("Can you summarize this file?")

    def test_generate_skill_content_yaml_frontmatter(self):
        from jarvis.multimodal.skill_creator import generate_skill_content

        content = generate_skill_content("stock-analyzer", "analyze stock market trends")
        assert content.startswith("---")
        assert "name: stock-analyzer" in content
        assert "description:" in content
        assert "# Analyze Stock Market Trends Skill" in content
        assert "## Core Workflows" in content
        assert "## Best Practices" in content

    def test_skill_creator_writes_to_disk(self, tmp_path):
        from jarvis.multimodal.skill_creator import SkillCreator

        global_dir = tmp_path / "global_skills"
        ws_dir = tmp_path / "ws_skills"
        creator = SkillCreator(global_skills_dir=global_dir, workspace_skills_dir=ws_dir)

        result = creator.create_skill("create a skill for automated backups")
        assert result.success
        assert result.skill_name == "automated-backups"
        assert "synthesized and installed" in result.message

        # Check global file
        global_file = global_dir / "automated-backups" / "SKILL.md"
        assert global_file.exists()
        content = global_file.read_text(encoding="utf-8")
        assert "name: automated-backups" in content

        # Check workspace file
        ws_file = ws_dir / "automated-backups" / "SKILL.md"
        assert ws_file.exists()
        ws_content = ws_file.read_text(encoding="utf-8")
        assert "name: automated-backups" in ws_content

    def test_assistant_dispatches_skill_creation(self, tmp_path):
        from jarvis.multimodal.jarvis_voice import JarvisVoiceAssistant

        global_dir = tmp_path / "global_skills"
        ws_dir = tmp_path / "ws_skills"

        assistant = JarvisVoiceAssistant(llm_provider="offline", greeting=False, verbose=False)
        assistant.skill_creator.global_skills_dir = global_dir
        assistant.skill_creator.workspace_skills_dir = ws_dir

        reply = assistant._think("Jarvis create a new skill to monitor gpu temperature")
        assert "synthesized and installed" in reply
        assert "monitor-gpu-temperature" in reply

        target_file = global_dir / "monitor-gpu-temperature" / "SKILL.md"
        assert target_file.exists()
