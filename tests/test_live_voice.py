from __future__ import annotations

"""Voice-out tests (`jarvis voice`) - audio is MEASURED, never assumed.

A Jarvis-like loop with no voice out is not a voice OS. These tests pin the
three things that make the audio real rather than claimed:

1. Engine resolution binds the first REAL synthesis engine this machine has
   (`JARVIS_TTS_CMD` override, `piper`, the Windows OS engine `System.Speech`,
   `espeak-ng`) and names the seam when there is none - with the probe list.
2. A payload is measured before it counts: a silent WAV, a non-WAV, and a
   synthesis fault are all reported as FAILED with NO audio written, the same
   posture the mission side takes on `exit 0` with no artifact.
3. When a real audio file is supplied, the turn-taking FSM is driven by
   per-frame RMS energy over the REAL samples instead of a caller-declared flag,
   and the reported speech/silence counts come from those samples.

The one test that can touch this machine's OS engine skips cleanly when no
engine is installed, so the suite stays honest on a bare box either way.
"""

import re
import shlex
import struct
import sys
import wave
from pathlib import Path

import pytest

from jarvis import cli
from jarvis import live as live_module
from jarvis.live import LiveRuntime

#: A hermetic fake TTS engine: a real process writing a real WAV whose
#: amplitude is argv[1] (0 = pure silence). argv[2] is the text file the seam
#: passes, argv[3] the target the seam asks for.
_WAV_WRITER = """
import math, struct, sys, wave
amplitude, rate, seconds = int(sys.argv[1]), 22050, 1.0
samples = [
    int(amplitude * math.sin(2 * math.pi * 440 * i / rate))
    for i in range(int(rate * seconds))
]
with wave.open(sys.argv[3], "wb") as handle:
    handle.setnchannels(1)
    handle.setsampwidth(2)
    handle.setframerate(rate)
    handle.writeframes(struct.pack(f"<{len(samples)}h", *samples))
"""


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    for name in (
        "JARVIS_MODEL_API_KEY",
        "JARVIS_MODEL_BASE_URL",
        "JARVIS_MODEL_NAME",
        "JARVIS_STT_CMD",
        "JARVIS_TTS_CMD",
    ):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def _fake_engine(tmp_path: Path, amplitude: int) -> str:
    """A `JARVIS_TTS_CMD` that writes a real WAV of the requested amplitude."""
    script = tmp_path / "fake_tts.py"
    script.write_text(_WAV_WRITER, encoding="utf-8")
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(script))} {amplitude}"


def _seeded_runtime(home: Path) -> LiveRuntime:
    """A runtime over a clean home with one memory the turn can answer from."""
    cli.main(["init"])
    cli.main(["say", "remember: the deploy gate runs on Thursdays"])
    service = cli.CoreService()
    service.start()
    return LiveRuntime(service)


def _sine_wav(path: Path, *, seconds: float, rate: int = 22050) -> None:
    """Half silence, then a loud tone: deterministic speech/silence frames."""
    samples: list[int] = []
    for index in range(int(rate * seconds)):
        middle = int(rate * seconds / 2)
        samples.append(16000 if index >= middle else 0)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(struct.pack(f"<{len(samples)}h", *samples))


# ---------------------------------------------------------------------------
# engine resolution
# ---------------------------------------------------------------------------


def test_no_engine_anywhere_names_the_seam_and_the_probes(monkeypatch):
    """With nothing installed the seam must name what was probed, not a guess."""
    monkeypatch.setattr(live_module.shutil, "which", lambda _name: None)
    runner, engine = live_module._resolve_tts_engine()

    assert runner is None
    assert engine.startswith("seam - no TTS engine resolvable")
    for probe in ("JARVIS_TTS_CMD", "piper", "Windows SAPI", "espeak-ng"):
        assert probe in engine


def test_explicit_command_wins_even_when_an_os_engine_exists(home, monkeypatch):
    """`JARVIS_TTS_CMD` is the user's override and keeps working unchanged."""
    monkeypatch.setenv("JARVIS_TTS_CMD", _fake_engine(home, 9000))
    runner, engine = live_module._resolve_tts_engine()

    assert runner is not None
    assert engine.startswith("real - JARVIS_TTS_CMD=")


# ---------------------------------------------------------------------------
# a synthesis is measured before it counts
# ---------------------------------------------------------------------------


def test_a_silent_wav_is_a_failed_synthesis_and_no_audio_is_written(home, monkeypatch):
    """Silence is not speech: the turn must refuse and say why."""
    monkeypatch.setenv("JARVIS_TTS_CMD", _fake_engine(home, 0))
    monkeypatch.setattr(
        "jarvis.live._resolve_stt_engine", lambda: (None, "seam - no engine bound")
    )
    runtime = _seeded_runtime(home)
    try:
        spoken = runtime.voice_turn("when does the deploy gate run")
    finally:
        runtime.service.close()

    assert spoken.answered is True  # there WAS something to say
    assert spoken.audio_out is None
    assert spoken.audio_non_silent is False
    assert any("FAILED" in line and "NO audio was produced" in line for line in spoken.lines)
    assert not (home / "audio").exists() or not list((home / "audio").iterdir())


def test_a_non_audio_payload_is_refused_instead_of_named_a_wav(home, monkeypatch):
    """A seam that writes something that is not a WAV is not audio out."""
    monkeypatch.setenv(
        "JARVIS_TTS_CMD",
        'python -c "import shutil,sys; shutil.copyfile(sys.argv[1], sys.argv[2])"',
    )
    monkeypatch.setattr(
        "jarvis.live._resolve_stt_engine", lambda: (None, "seam - no engine bound")
    )
    runtime = _seeded_runtime(home)
    try:
        spoken = runtime.voice_turn("when does the deploy gate run")
    finally:
        runtime.service.close()

    assert spoken.audio_out is None
    assert any("FAILED" in line for line in spoken.lines)


def test_real_synthesis_is_measured_and_written_with_its_facts(home, monkeypatch):
    """A real WAV payload is parsed: duration, rate, peak - then written."""
    monkeypatch.setenv("JARVIS_TTS_CMD", _fake_engine(home, 9000))
    monkeypatch.setattr(
        "jarvis.live._resolve_stt_engine", lambda: (None, "seam - no engine bound")
    )
    runtime = _seeded_runtime(home)
    try:
        spoken = runtime.voice_turn("when does the deploy gate run")
    finally:
        runtime.service.close()

    assert spoken.audio_out is not None
    assert spoken.audio_non_silent is True
    assert spoken.audio_sample_rate == 22050
    assert 0.9 <= spoken.audio_seconds <= 1.1
    assert 0.0 < spoken.audio_peak <= 1.0
    written = Path(spoken.audio_out)
    assert written.is_file() and written.stat().st_size > 0
    assert any("measured non-silent" in line for line in spoken.lines)


# ---------------------------------------------------------------------------
# real audio in: measured VAD over real samples
# ---------------------------------------------------------------------------


def test_real_audio_frames_drive_the_fsm_with_measured_vad(home, monkeypatch):
    """The input side is data, not a pre-set bool: frames come from the file."""
    monkeypatch.setattr(
        "jarvis.live._resolve_stt_engine", lambda: (None, "seam - no engine bound")
    )
    monkeypatch.setattr(
        "jarvis.live._resolve_tts_engine", lambda: (None, "seam - no engine bound")
    )
    source = home / "spoken.wav"
    _sine_wav(source, seconds=1.0)
    runtime = _seeded_runtime(home)
    try:
        spoken = runtime.voice_turn("typed text the audio should replace", audio=source)
    finally:
        runtime.service.close()

    assert spoken.vad.startswith("real - ")
    assert "frames @" in spoken.vad
    assert "speech /" in spoken.vad
    assert "user_speaking" in spoken.states
    match = re.search(r"\((\d+) speech / (\d+) silence", spoken.vad)
    assert match is not None
    speech, silence = int(match.group(1)), int(match.group(2))
    assert speech > 0 and silence > 0
    assert speech < speech + silence


def test_a_typed_turn_declares_that_nothing_was_captured(home, monkeypatch):
    """No audio, no VAD claim: the turn says nothing was captured."""
    monkeypatch.setattr(
        "jarvis.live._resolve_stt_engine", lambda: (None, "seam - no engine bound")
    )
    monkeypatch.setattr(
        "jarvis.live._resolve_tts_engine", lambda: (None, "seam - no engine bound")
    )
    runtime = _seeded_runtime(home)
    try:
        spoken = runtime.voice_turn("when does the deploy gate run")
    finally:
        runtime.service.close()

    assert spoken.vad.startswith("caller-declared")
    assert "no microphone was opened" in spoken.vad


# ---------------------------------------------------------------------------
# this machine, for real
# ---------------------------------------------------------------------------


def test_this_machine_speaks_or_says_why_it_cannot(home, monkeypatch):
    """The box's own engine, exercised end to end - or the seam, named.

    On this machine the resolved engine is the Windows OS voice
    (`System.Speech`); on a box with none the seam is asserted instead, so the
    test never claims audio it did not produce.
    """
    monkeypatch.setattr(
        "jarvis.live._resolve_stt_engine", lambda: (None, "seam - no engine bound")
    )
    runner, engine = live_module._resolve_tts_engine()
    if runner is None:
        assert engine.startswith("seam - ")
        pytest.skip(f"no TTS engine on this machine: {engine}")

    runtime = _seeded_runtime(home)
    try:
        spoken = runtime.voice_turn("when does the deploy gate run")
    finally:
        runtime.service.close()

    assert any(line.startswith("tts: ") and engine in line for line in spoken.lines)
    assert spoken.audio_out is not None, spoken.lines
    assert spoken.audio_non_silent is True, spoken.lines
    assert spoken.audio_seconds > 0.2, spoken.lines
    assert spoken.audio_sample_rate > 0
    payload = Path(spoken.audio_out).read_bytes()
    assert len(payload) > 1000
    with wave.open(str(spoken.audio_out), "rb") as handle:  # independently re-parsed
        assert handle.getnframes() > 0
        assert handle.getframerate() == spoken.audio_sample_rate
