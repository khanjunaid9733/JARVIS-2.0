from __future__ import annotations

"""Unit tests for Streaming Voice Loop & Barge-In FSM (src/jarvis/multimodal/streaming.py)."""

from pathlib import Path

import pytest

from jarvis.kernel.event_log import EventLog
from jarvis.multimodal.streaming import StreamingVoiceLoop, VoiceTurnState


def test_streaming_voice_loop_normal_turn():
    loop = StreamingVoiceLoop(silence_threshold_frames=3)
    assert loop.state == VoiceTurnState.IDLE

    # Start listening
    loop.start_listening()
    assert loop.state == VoiceTurnState.LISTENING

    # User starts speaking (VAD active)
    st = loop.feed_audio_frame(b"audio_chunk_1", vad_active=True)
    assert st == VoiceTurnState.USER_SPEAKING

    # User continues speaking
    loop.feed_audio_frame(b"audio_chunk_2", vad_active=True)
    assert loop.state == VoiceTurnState.USER_SPEAKING

    # Silence detected (3 consecutive silent frames)
    loop.feed_audio_frame(b"silence_1", vad_active=False)
    assert loop.state == VoiceTurnState.USER_SPEAKING
    loop.feed_audio_frame(b"silence_2", vad_active=False)
    assert loop.state == VoiceTurnState.USER_SPEAKING
    loop.feed_audio_frame(b"silence_3", vad_active=False)
    # Threshold reached -> THINKING
    assert loop.state == VoiceTurnState.THINKING

    # Audio buffer collected
    audio = loop.get_collected_audio()
    assert b"audio_chunk_1" in audio
    assert b"audio_chunk_2" in audio

    # Assistant speaks
    loop.start_assistant_speaking()
    assert loop.state == VoiceTurnState.ASSISTANT_SPEAKING

    # Assistant finishes
    loop.finish_assistant_speaking()
    assert loop.state == VoiceTurnState.LISTENING


def test_streaming_voice_loop_barge_in_interruption():
    interrupted = False

    def on_interrupted():
        nonlocal interrupted
        interrupted = True

    loop = StreamingVoiceLoop(on_interrupted=on_interrupted)

    # Assistant is currently speaking
    loop.start_assistant_speaking()
    assert loop.state == VoiceTurnState.ASSISTANT_SPEAKING

    # User interrupts by speaking (VAD active)
    st = loop.feed_audio_frame(b"user_interrupt_speech", vad_active=True)

    # Interruption triggered and state transitions to USER_SPEAKING
    assert interrupted is True
    assert st == VoiceTurnState.USER_SPEAKING
    assert loop.get_collected_audio() == b"user_interrupt_speech"


def test_streaming_voice_loop_with_event_log(tmp_path: Path):
    log = EventLog(tmp_path / "voice_events.db")
    loop = StreamingVoiceLoop(event_log=log)

    loop.start_listening()
    loop.feed_audio_frame(b"frame", vad_active=True)
    loop.reset()

    events = log.replay(since=0)
    assert len(events) >= 2
    assert all(e.event_type == "multimodal.voice_state_changed" for e in events)
