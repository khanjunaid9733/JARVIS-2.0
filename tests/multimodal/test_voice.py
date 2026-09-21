from __future__ import annotations

"""Unit tests for Whisper STT and Piper TTS adapters (src/jarvis/multimodal/voice.py)."""

import base64
from pathlib import Path

import pytest

from jarvis.kernel.model_gateway import ProviderTransportError
from jarvis.multimodal.voice import PiperTTSAdapter, WhisperSTTAdapter


# ---------------------------------------------------------------------------
# Whisper STT Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_whisper_stt_transcribe_bytes():
    adapter = WhisperSTTAdapter()
    res = await adapter.invoke(
        "audio.transcribe",
        "1.0.0",
        {"audio_bytes": b"RIFF....WAVEdata12345", "format": "wav", "language": "en"},
    )
    assert "text" in res
    assert res["language"] == "en"
    assert len(res["segments"]) == 1
    assert res["model"] == "whisper-base"


@pytest.mark.anyio
async def test_whisper_stt_transcribe_base64():
    adapter = WhisperSTTAdapter()
    b64_audio = base64.b64encode(b"sample_audio_payload").decode("utf-8")
    res = await adapter.invoke(
        "audio.transcribe",
        "1.0.0",
        {"audio_bytes": b64_audio, "format": "mp3"},
    )
    assert "text" in res


@pytest.mark.anyio
async def test_whisper_stt_transcribe_file_path(tmp_path: Path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"RIFF_test_wav_content")

    adapter = WhisperSTTAdapter()
    res = await adapter.invoke(
        "audio.transcribe",
        "1.0.0",
        {"audio_path": str(audio_file)},
    )
    assert "text" in res


@pytest.mark.anyio
async def test_whisper_stt_unsupported_contract_raises_transport_error():
    adapter = WhisperSTTAdapter()
    with pytest.raises(ProviderTransportError) as exc_info:
        await adapter.invoke("audio.unsupported", "1.0.0", {"audio_bytes": b"123"})
    assert "does not support contract" in str(exc_info.value)


@pytest.mark.anyio
async def test_whisper_stt_missing_audio_raises_transport_error():
    adapter = WhisperSTTAdapter()
    with pytest.raises(ProviderTransportError) as exc_info:
        await adapter.invoke("audio.transcribe", "1.0.0", {})
    assert "requires 'audio_bytes'" in str(exc_info.value)


def test_whisper_stt_health_check():
    adapter = WhisperSTTAdapter()
    assert adapter.health_check() is True

    # Failing runner
    broken = WhisperSTTAdapter(runner=lambda *args: {})
    assert broken.health_check() is False


# ---------------------------------------------------------------------------
# Piper TTS Tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_piper_tts_synthesize_success():
    adapter = PiperTTSAdapter(voice="en_US-lessac-medium")
    res = await adapter.invoke(
        "audio.synthesize",
        "1.0.0",
        {"text": "Hello JARVIS", "voice": "en_US-lessac-medium", "format": "wav"},
    )
    assert "audio_bytes" in res
    assert res["format"] == "wav"
    assert res["voice"] == "en_US-lessac-medium"
    assert res["sample_rate"] == 22050


@pytest.mark.anyio
async def test_piper_tts_empty_text_raises_transport_error():
    adapter = PiperTTSAdapter()
    with pytest.raises(ProviderTransportError) as exc_info:
        await adapter.invoke("audio.synthesize", "1.0.0", {"text": "   "})
    assert "requires non-empty string" in str(exc_info.value)


@pytest.mark.anyio
async def test_piper_tts_unsupported_contract_raises_transport_error():
    adapter = PiperTTSAdapter()
    with pytest.raises(ProviderTransportError) as exc_info:
        await adapter.invoke("audio.wrong", "1.0.0", {"text": "hi"})
    assert "does not support contract" in str(exc_info.value)


def test_piper_tts_health_check():
    adapter = PiperTTSAdapter()
    assert adapter.health_check() is True

    broken = PiperTTSAdapter(runner=lambda *args: {})
    assert broken.health_check() is False
