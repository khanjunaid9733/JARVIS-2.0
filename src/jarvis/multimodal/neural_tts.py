"""Neural Text-to-Speech Engine — High-Quality Voice Synthesis.

Provides:
- NeuralTTSEngine: Edge TTS integration with fallback to SAPI/pyttsx3.
- TTSResult: Measured WAV output with duration, peak, and non-silence check.

Uses Microsoft Edge TTS (free, neural-quality, multiple voices) as the
primary synthesis engine. Falls back gracefully to pyttsx3 (which wraps
SAPI on Windows) when Edge TTS is unavailable or network is down.

Invariants:
1. Every synthesis output is MEASURED before it counts — silent WAVs are
   rejected exactly as silent STT buffers are.
2. The caller receives raw WAV bytes + measured facts, never assumed.
3. This module sits behind the existing PiperTTSAdapter seam — it can be
   injected as the runner function.
"""

from __future__ import annotations

import asyncio
import io
import struct
import tempfile
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class TTSResult:
    """Measured synthesis output."""

    audio_bytes: bytes
    duration_seconds: float
    sample_rate: int
    channels: int
    peak: float
    rms: float
    non_silent: bool
    engine: str
    voice: str


SILENCE_PEAK_THRESHOLD = 0.005


def _measure_wav(audio_bytes: bytes) -> dict[str, Any]:
    """Parse and measure a WAV payload."""
    with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if width == 2:
        count = len(raw) // 2
        samples = [v / 32768.0 for v in struct.unpack(f"<{count}h", raw[:count * 2])]
    elif width == 1:
        samples = [(v - 128) / 128.0 for v in raw]
    else:
        count = len(raw) // 4
        samples = [v / 2147483648.0 for v in struct.unpack(f"<{count}i", raw[:count * 4])]

    if not samples:
        return {"duration_seconds": 0, "sample_rate": rate, "channels": channels,
                "peak": 0, "rms": 0, "non_silent": False}

    peak = max(abs(s) for s in samples)
    rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
    duration = (n_frames / channels) / rate if rate > 0 else 0

    return {
        "duration_seconds": duration,
        "sample_rate": rate,
        "channels": channels,
        "peak": peak,
        "rms": rms,
        "non_silent": peak > SILENCE_PEAK_THRESHOLD,
    }


# ---------------------------------------------------------------------------
# Edge TTS (neural, free, Microsoft Azure voices)
# ---------------------------------------------------------------------------

# Voices ranked by JARVIS-appropriateness
EDGE_VOICES = {
    "jarvis": "en-US-GuyNeural",           # Deep, calm male — closest to JARVIS
    "jarvis_uk": "en-GB-RyanNeural",       # British male — more Paul Bettany
    "professional": "en-US-DavisNeural",    # Professional male
    "female": "en-US-JennyNeural",          # Friendly female
    "friendly": "en-US-ChristopherNeural",  # Warm male
}

DEFAULT_VOICE = "en-GB-RyanNeural"  # British male for that JARVIS feel


async def _edge_tts_synthesize(
    text: str, voice: str = DEFAULT_VOICE, rate: str = "+0%", pitch: str = "+0Hz"
) -> bytes:
    """Synthesize speech using Edge TTS (async)."""
    import edge_tts

    with tempfile.TemporaryDirectory() as tmp:
        output_path = Path(tmp) / "speech.mp3"
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        await communicate.save(str(output_path))

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Edge TTS produced no output")

        mp3_bytes = output_path.read_bytes()

    # Convert MP3 to WAV for consistent pipeline
    wav_bytes = _mp3_to_wav(mp3_bytes)
    return wav_bytes


def _mp3_to_wav(mp3_bytes: bytes) -> bytes:
    """Convert MP3 bytes to WAV bytes using available decoders."""
    import subprocess
    import shutil

    # Try ffmpeg first
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        with tempfile.TemporaryDirectory() as tmp:
            mp3_path = Path(tmp) / "input.mp3"
            wav_path = Path(tmp) / "output.wav"
            mp3_path.write_bytes(mp3_bytes)
            result = subprocess.run(
                [ffmpeg, "-i", str(mp3_path), "-ar", "24000", "-ac", "1",
                 "-f", "wav", str(wav_path), "-y", "-loglevel", "quiet"],
                capture_output=True, timeout=30,
            )
            if result.returncode == 0 and wav_path.exists():
                return wav_path.read_bytes()

    # Try pydub
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
        wav_buffer = io.BytesIO()
        audio.export(wav_buffer, format="wav")
        return wav_buffer.getvalue()
    except ImportError:
        pass

    # Try scipy
    try:
        import numpy as np
        # scipy can't read mp3 natively, but we can try via soundfile
        import soundfile as sf
        data, samplerate = sf.read(io.BytesIO(mp3_bytes))
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, data, samplerate, format="WAV")
        return wav_buffer.getvalue()
    except (ImportError, Exception):
        pass

    raise RuntimeError(
        "Cannot convert MP3 to WAV: install ffmpeg (recommended), pydub, or soundfile"
    )


# ---------------------------------------------------------------------------
# pyttsx3 fallback (offline, SAPI-based on Windows)
# ---------------------------------------------------------------------------

def _pyttsx3_synthesize(text: str, voice_id: str | None = None, rate: int = 180) -> bytes:
    """Synthesize speech using pyttsx3 (offline fallback)."""
    import pyttsx3

    engine = pyttsx3.init()
    engine.setProperty("rate", rate)

    if voice_id:
        engine.setProperty("voice", voice_id)
    else:
        # Try to find a suitable voice
        voices = engine.getProperty("voices")
        for v in voices:
            if "david" in v.name.lower() or "male" in v.name.lower():
                engine.setProperty("voice", v.id)
                break

    with tempfile.TemporaryDirectory() as tmp:
        output_path = Path(tmp) / "speech.wav"
        engine.save_to_file(text, str(output_path))
        engine.runAndWait()

        if not output_path.exists():
            raise RuntimeError("pyttsx3 produced no output file")

        return output_path.read_bytes()


# ---------------------------------------------------------------------------
# Unified NeuralTTSEngine
# ---------------------------------------------------------------------------

class NeuralTTSEngine:
    """High-quality TTS with Edge TTS primary and pyttsx3 fallback.

    This engine can be injected as the `runner` for PiperTTSAdapter, or used
    directly by the voice loop.
    """

    def __init__(
        self,
        *,
        voice: str = DEFAULT_VOICE,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        pyttsx3_rate: int = 180,
        prefer_edge: bool = True,
    ) -> None:
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.pyttsx3_rate = pyttsx3_rate
        self.prefer_edge = prefer_edge
        self._edge_available: bool | None = None

    def _check_edge_available(self) -> bool:
        """Check if edge_tts is importable."""
        if self._edge_available is not None:
            return self._edge_available
        try:
            import edge_tts  # noqa: F401
            self._edge_available = True
        except ImportError:
            self._edge_available = False
        return self._edge_available

    def synthesize(self, text: str) -> TTSResult:
        """Synthesize speech and return measured WAV output.

        Tries Edge TTS first (neural quality), falls back to pyttsx3.
        Every output is MEASURED before it counts.
        """
        if not text or not text.strip():
            raise ValueError("Cannot synthesize empty text")

        audio_bytes: bytes | None = None
        engine_name = "unknown"

        # Try Edge TTS first
        if self.prefer_edge and self._check_edge_available():
            try:
                loop = None
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    pass

                if loop and loop.is_running():
                    # Already in an async context — run in a new thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(
                            asyncio.run,
                            _edge_tts_synthesize(text, self.voice, self.rate, self.pitch),
                        )
                        audio_bytes = future.result(timeout=30)
                else:
                    audio_bytes = asyncio.run(
                        _edge_tts_synthesize(text, self.voice, self.rate, self.pitch)
                    )
                engine_name = f"edge-tts ({self.voice})"
            except Exception:
                audio_bytes = None

        # Fallback to pyttsx3
        if audio_bytes is None:
            try:
                audio_bytes = _pyttsx3_synthesize(text, rate=self.pyttsx3_rate)
                engine_name = "pyttsx3 (SAPI fallback)"
            except Exception as exc:
                raise RuntimeError(f"All TTS engines failed. Last error: {exc}") from exc

        # MEASURE the output — never assume it's valid
        try:
            facts = _measure_wav(audio_bytes)
        except Exception as exc:
            raise RuntimeError(f"TTS produced invalid WAV: {exc}") from exc

        if not facts["non_silent"]:
            raise RuntimeError(f"TTS ({engine_name}) produced a silent WAV (peak={facts['peak']:.4f})")

        return TTSResult(
            audio_bytes=audio_bytes,
            duration_seconds=facts["duration_seconds"],
            sample_rate=facts["sample_rate"],
            channels=facts["channels"],
            peak=facts["peak"],
            rms=facts["rms"],
            non_silent=facts["non_silent"],
            engine=engine_name,
            voice=self.voice,
        )

    def make_runner(self) -> Any:
        """Return a runner function compatible with PiperTTSAdapter interface."""
        def runner(text: str, voice: str, output_format: str) -> dict[str, Any]:
            result = self.synthesize(text)
            return {
                "audio_bytes": result.audio_bytes,
                "sample_rate": result.sample_rate,
                "format": output_format,
                "voice": result.voice,
                "duration_seconds": result.duration_seconds,
                "engine": result.engine,
            }
        return runner


__all__ = [
    "DEFAULT_VOICE",
    "EDGE_VOICES",
    "NeuralTTSEngine",
    "TTSResult",
]
