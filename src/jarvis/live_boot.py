from __future__ import annotations

"""Bootstrap and configuration - the ONE place a live runtime is assembled.

`boot_runtime` builds the components the live loop runs on and nothing else:

* memory kernel - `CoreService`: creator identity, hash-chained `EventLog`,
  `MemoryProjection`, seeded registry.
* effect + filesystem - the path-jailed `FilesystemSandbox` and the live
  adapters dict the effect envelope is opened against.
* orchestrator - `CapabilityRegistry`, `Router` (L5 roles), `RecoveryEngine`
  (M3.4 ladder) and `SupervisorDaemon` (M3.5), each constructed, none exercised
  here, plus the L7 bridge identities.
* multimodal - the STT/TTS engines THIS machine really has bound, resolved by
  `_resolve_stt_engine` / `_resolve_tts_engine` and named honestly (`real - ...`
  or `seam - ...`). Presence only binds an engine; a voice turn MEASURES the
  audio before it may claim it spoke.
* capability fabric seam - the `CapabilityResolver` (see
  `jarvis.live_capability`) that the mission's steps resolve their declared needs
  through. The fabric itself is imported on first USE, never here.

What is configuration and what is behaviour are kept apart on purpose: this
module decides WHICH engines and components exist (and says so in the labels it
returns), while `jarvis.live_steps` declares what the steps are,
`jarvis.live_capability` resolves a step's declared need, `jarvis.live_dispatch`
runs and adjudicates the work, and `jarvis.live_report` owns every word printed.
"""

import io
import os
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from .bootstrap import CoreService
from .effects.filesystem import FilesystemEffectAdapter, FilesystemSandbox
from .kernel.event_log import EventLog
from .kernel.registry import CapabilityRegistry
from .live_capability import CapabilityResolver
from .multimodal.voice import PiperTTSAdapter, WhisperSTTAdapter
from .orchestrator import AgyBridge, DeepSeekBridge, OpenCodeBridge
from .orchestrator.daemon import Lease, SupervisorDaemon
from .orchestrator.recovery_engine import RecoveryEngine
from .orchestrator.router import Router
from .supervisor import RecoveryPolicy

if TYPE_CHECKING:  # typing only: the fabric is imported on first USE, see below
    from .skills.engine import SkillRuntimeEngine

WORKSPACE_DIRNAME = "workspace"
AUDIO_DIRNAME = "audio"
LEASE_TTL_SECONDS = 3600.0


class LiveError(RuntimeError):
    """A live-loop precondition fault (never a worker failure)."""


# ---------------------------------------------------------------------------
# engine resolution: real engine or an honestly named seam
# ---------------------------------------------------------------------------


def _stt_command_runner(command: str) -> Callable[[bytes, str, str | None], dict[str, Any]]:
    """`<command> <audio_path>` -> transcript on stdout (real subprocess)."""

    def run(audio_bytes: bytes, audio_format: str, language: str | None) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / f"turn.{audio_format or 'wav'}"
            source.write_bytes(audio_bytes)
            proc = subprocess.run(
                shlex.split(command) + [str(source)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=900,
                shell=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"stt command exited {proc.returncode}: {proc.stderr[-300:]}")
            return {
                "text": proc.stdout.strip(),
                "language": language or "en",
                "duration_seconds": 0.0,
                "model": command,
                "engine": command,
            }

    return run


def _faster_whisper_runner(model_name: str) -> Callable[[bytes, str, str | None], dict[str, Any]]:
    """In-process faster-whisper inference (real; the model downloads on first use)."""

    def run(audio_bytes: bytes, audio_format: str, language: str | None) -> dict[str, Any]:
        from faster_whisper import WhisperModel

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / f"turn.{audio_format or 'wav'}"
            source.write_bytes(audio_bytes)
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
            segments, info = model.transcribe(str(source), language=language)
            text = " ".join(segment.text.strip() for segment in segments).strip()
            return {
                "text": text,
                "language": info.language,
                "duration_seconds": float(info.duration),
                "model": model_name,
                "engine": f"faster-whisper:{model_name}",
            }

    return run


def _whisper_cli_runner(binary: str) -> Callable[[bytes, str, str | None], dict[str, Any]]:
    """The openai-whisper CLI (real subprocess; downloads its model on first use)."""

    model_name = os.environ.get("JARVIS_STT_MODEL", "base")

    def run(audio_bytes: bytes, audio_format: str, language: str | None) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / f"turn.{audio_format or 'wav'}"
            source.write_bytes(audio_bytes)
            command = [
                binary,
                "--model",
                model_name,
                "--output_format",
                "txt",
                "--output_dir",
                tmp,
            ]
            if language:
                command += ["--language", language]
            command.append(str(source))
            proc = subprocess.run(
                command, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=1800, shell=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"whisper CLI exited {proc.returncode}: {proc.stderr[-300:]}")
            transcript = Path(tmp) / "turn.txt"
            return {
                "text": transcript.read_text(encoding="utf-8").strip() if transcript.exists() else "",
                "language": language or "en",
                "duration_seconds": 0.0,
                "model": model_name,
                "engine": f"whisper-cli:{model_name}",
            }

    return run


def _tts_command_runner(command: str) -> Callable[[str, str, str], dict[str, Any]]:
    """`<command> <text_file> <out_file>` -> audio bytes read back (real subprocess)."""

    def run(text: str, voice: str, output_format: str) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "turn.txt"
            source.write_text(text, encoding="utf-8")
            target = Path(tmp) / f"turn.{output_format or 'wav'}"
            proc = subprocess.run(
                shlex.split(command) + [str(source), str(target)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=900,
                shell=False,
            )
            if proc.returncode != 0 or not target.exists():
                raise RuntimeError(
                    f"tts command exited {proc.returncode}: {proc.stderr[-300:]}"
                )
            return {
                "audio_bytes": target.read_bytes(),
                "sample_rate": 22050,
                "format": output_format,
                "voice": voice,
                "duration_seconds": 0.0,
                "engine": command,
            }

    return run


def _resolve_stt_engine() -> tuple[Callable[..., dict[str, Any]] | None, str]:
    command = os.environ.get("JARVIS_STT_CMD", "").strip()
    if command:
        return _stt_command_runner(command), f"real - JARVIS_STT_CMD={command}"
    try:
        import faster_whisper

        version = getattr(faster_whisper, "__version__", "?")
    except Exception:
        pass
    else:
        model = os.environ.get("JARVIS_STT_MODEL", "tiny")
        return (
            _faster_whisper_runner(model),
            f"real - faster-whisper {version} (model {model}; downloads on first use)",
        )
    binary = shutil.which("whisper")
    if binary:
        return _whisper_cli_runner(binary), f"real - whisper CLI ({binary})"
    return None, "seam - no engine bound (set JARVIS_STT_CMD, or install faster-whisper / whisper)"


#: A frame counts as speech when its RMS energy exceeds this fraction of full
#: scale. Measured per frame, never declared: the counts are printed.
VAD_RMS_THRESHOLD = 0.01
VAD_FRAME_MS = 30
#: Below this peak a WAV is silence, i.e. a FAILED synthesis, not audio.
SILENCE_PEAK_THRESHOLD = 0.005


def _decode_samples(raw: bytes, width: int) -> list[float]:
    """PCM bytes -> normalised floats in [-1, 1]."""
    if width == 1:
        return [(value - 128) / 128.0 for value in raw]
    if width == 2:
        count = len(raw) // 2
        return [value / 32768.0 for value in struct.unpack(f"<{count}h", raw[: count * 2])]
    if width == 4:
        count = len(raw) // 4
        return [value / 2147483648.0 for value in struct.unpack(f"<{count}i", raw[: count * 4])]
    raise ValueError(f"unsupported sample width: {width}")


def _wav_facts(audio_bytes: bytes) -> dict[str, Any]:
    """MEASURE a WAV payload instead of trusting that synthesis happened.

    Returns duration / sample rate / channels / peak / RMS and `non_silent`. An
    unparseable or all-silent payload is a failed synthesis, exactly as `exit 0`
    with no artifact is a failed step on the mission side.
    """
    with wave.open(io.BytesIO(audio_bytes), "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        rate = handle.getframerate()
        frames = handle.getnframes()
        raw = handle.readframes(frames)
    if channels < 1 or rate <= 0:
        raise ValueError(f"unsupported WAV layout (channels={channels}, rate={rate})")
    samples = _decode_samples(raw, width)
    if not samples:
        raise ValueError("WAV carries no samples")
    peak = max(abs(sample) for sample in samples)
    rms = (sum(sample * sample for sample in samples) / len(samples)) ** 0.5
    return {
        "duration_seconds": (frames / channels) / rate,
        "sample_rate": rate,
        "channels": channels,
        "peak": peak,
        "rms": rms,
        "samples": len(samples),
        "non_silent": peak > SILENCE_PEAK_THRESHOLD,
    }


def _wav_vad_frames(audio_bytes: bytes) -> list[tuple[bytes, bool]] | None:
    """Slice a real WAV into frames with a MEASURED activity flag per frame.

    Returns None when the payload is not a simple PCM WAV (an mp3 or a container
    the STT engine may still decode): the caller then declares VAD instead of
    inventing it.
    """
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as handle:
            rate = handle.getframerate()
            width = handle.getsampwidth()
            channels = handle.getnchannels()
            raw = handle.readframes(handle.getnframes())
    except Exception:
        return None
    if channels < 1 or rate <= 0 or width not in (1, 2, 4) or not raw:
        return None
    block = max(width * channels, int(rate * VAD_FRAME_MS / 1000) * width * channels)
    frames: list[tuple[bytes, bool]] = []
    for start in range(0, len(raw), block):
        chunk = raw[start : start + block]
        samples = _decode_samples(chunk, width)
        rms = (sum(sample * sample for sample in samples) / len(samples)) ** 0.5
        frames.append((chunk, rms > VAD_RMS_THRESHOLD))
    return frames


def _sapi_tts_runner(powershell: str) -> Callable[[str, str, str], dict[str, Any]]:
    """Windows SAPI (`System.Speech`) synthesis - the OS engine, installed already.

    The text arrives on stdin via `[Console]::In.ReadToEnd()`, so no user text is
    ever interpolated into a command line or a script body.
    """
    engine = "real - Windows SAPI (System.Speech) via powershell"

    def run(text: str, voice: str, output_format: str) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / f"turn.{output_format or 'wav'}"
            script = (
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.SetOutputToWaveFile('{target}'); "
                "$s.Speak([Console]::In.ReadToEnd()); "
                "$s.Dispose()"
            )
            proc = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    script,
                ],
                input=text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=900,
                shell=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"SAPI exited {proc.returncode}: {proc.stderr[-300:]}")
            if not target.exists():
                raise RuntimeError("SAPI reported success but wrote no audio file")
            audio = target.read_bytes()
            facts = _wav_facts(audio)
            if not facts["non_silent"]:
                raise RuntimeError("SAPI produced a silent WAV (peak is zero)")
            return {
                "audio_bytes": audio,
                "sample_rate": facts["sample_rate"],
                "format": output_format,
                "voice": voice,
                "duration_seconds": facts["duration_seconds"],
                "engine": engine,
            }

    return run


def _espeak_tts_runner(binary: str) -> Callable[[str, str, str], dict[str, Any]]:
    """`espeak-ng -w <out.wav> -f <text file>` -> measured WAV bytes."""
    engine = f"real - espeak-ng CLI ({binary})"

    def run(text: str, voice: str, output_format: str) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "turn.txt"
            source.write_text(text, encoding="utf-8")
            target = Path(tmp) / f"turn.{output_format or 'wav'}"
            proc = subprocess.run(
                [binary, "-w", str(target), "-f", str(source)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=900,
                shell=False,
            )
            if proc.returncode != 0 or not target.exists():
                raise RuntimeError(f"espeak-ng exited {proc.returncode}: {proc.stderr[-300:]}")
            audio = target.read_bytes()
            facts = _wav_facts(audio)
            if not facts["non_silent"]:
                raise RuntimeError("espeak-ng produced a silent WAV (peak is zero)")
            return {
                "audio_bytes": audio,
                "sample_rate": facts["sample_rate"],
                "format": output_format,
                "voice": voice,
                "duration_seconds": facts["duration_seconds"],
                "engine": engine,
            }

    return run


def _resolve_tts_engine() -> tuple[Callable[..., dict[str, Any]] | None, str]:
    """Bind the first REAL synthesis engine on this machine, else name the seam.

    Probed in order: `JARVIS_TTS_CMD` (explicit override - always wins, and the
    contract `<command> <text_file> <out_file>` is unchanged), `piper`, the
    Windows OS engine `System.Speech` through powershell, then `espeak-ng`.
    Presence only binds the engine; the audio itself is measured (`_wav_facts`)
    before a turn may claim it spoke.
    """
    command = os.environ.get("JARVIS_TTS_CMD", "").strip()
    if command:
        return _tts_command_runner(command), f"real - JARVIS_TTS_CMD={command}"
    binary = shutil.which("piper")
    if binary:
        return _tts_command_runner(binary), f"real - piper CLI ({binary})"
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if powershell and sys.platform == "win32":
        return _sapi_tts_runner(powershell), (
            "real - Windows SAPI (System.Speech) via powershell; the OS voice"
        )
    binary = shutil.which("espeak-ng") or shutil.which("espeak")
    if binary:
        return _espeak_tts_runner(binary), f"real - espeak-ng CLI ({binary})"
    return (
        None,
        "seam - no TTS engine resolvable (probed JARVIS_TTS_CMD, piper, Windows SAPI, "
        "espeak-ng); NO audio is produced",
    )


# ---------------------------------------------------------------------------
# the bootstrap: which components exist, and which engines really bound
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuntimeBoot:
    """Everything a `LiveRuntime` is made of, constructed and labeled once.

    `stt_engine`/`tts_engine` are the honest labels for what really bound
    (`real - ...` / `seam - ...`); `stt`/`tts` are the adapters (None when no
    engine bound, so a turn can never be fed a deterministic default runner and
    reported as perception). `leases` is the live list the daemon adjudicates.
    """

    service: CoreService
    home: Path
    log: EventLog
    workspace: Path
    sandbox: FilesystemSandbox
    adapters: dict[str, Any]
    catalog: CapabilityRegistry
    router: Router
    recovery: RecoveryEngine
    supervisor_id: str
    daemon: SupervisorDaemon
    bridges: dict[str, Any]
    stt: Any
    stt_engine: str
    tts: Any
    tts_engine: str
    capabilities: CapabilityResolver
    dispatch_path: Path
    leases_path: Path
    leases: list[Lease] = field(default_factory=list)


def boot_runtime(
    service: CoreService,
    *,
    supervisor_instance_id: str | None = None,
    skill_engine: SkillRuntimeEngine | None = None,
    resolve_stt: Callable[..., Any] = _resolve_stt_engine,
    resolve_tts: Callable[..., Any] = _resolve_tts_engine,
) -> RuntimeBoot:
    """Assemble the live components from the real configuration on this machine.

    `resolve_stt`/`resolve_tts` are injectable so a deployment (or a test) can
    substitute an engine resolver without touching the composition root; the
    defaults bind whatever this machine really has.
    """
    home = service.home
    log: EventLog = service.log  # type: ignore[assignment]
    workspace = home / WORKSPACE_DIRNAME
    # The jail root must exist before ANY dispatch: an external worker is
    # spawned with cwd=workspace, and a missing directory fails the spawn.
    workspace.mkdir(parents=True, exist_ok=True)
    sandbox = FilesystemSandbox(workspace)
    adapters: dict[str, Any] = {"fs.default": FilesystemEffectAdapter(sandbox)}
    # Live catalog is in-memory (log=None): registering the live providers
    # appends NOTHING, so the §127.1 "4 providers" projection stays intact.
    catalog = CapabilityRegistry.seed_m1_defaults()
    router = Router()
    recovery = RecoveryEngine(policy=RecoveryPolicy(), git=None, package="live-loop")
    supervisor_id = supervisor_instance_id or (
        "sup-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    )
    daemon = SupervisorDaemon(
        heartbeat_stale_after=LEASE_TTL_SECONDS,
        current_supervisor_instance_id=supervisor_id,
    )
    bridges = {
        "bigpickle": OpenCodeBridge(),
        "freebuff": DeepSeekBridge(),
        "antigravity": AgyBridge(),
    }
    stt_runner, stt_engine = resolve_stt()
    tts_runner, tts_engine = resolve_tts()
    return RuntimeBoot(
        service=service,
        home=home,
        log=log,
        workspace=workspace,
        sandbox=sandbox,
        adapters=adapters,
        catalog=catalog,
        router=router,
        recovery=recovery,
        supervisor_id=supervisor_id,
        daemon=daemon,
        bridges=bridges,
        stt=WhisperSTTAdapter(runner=stt_runner) if stt_runner else None,
        stt_engine=stt_engine,
        tts=PiperTTSAdapter(runner=tts_runner) if tts_runner else None,
        tts_engine=tts_engine,
        capabilities=CapabilityResolver(
            workspace=workspace,
            sandbox=sandbox,
            log=log,
            engine=skill_engine,
        ),
        dispatch_path=home / "dispatches.jsonl",
        leases_path=home / "leases.jsonl",
    )


__all__ = [
    "AUDIO_DIRNAME",
    "LEASE_TTL_SECONDS",
    "LiveError",
    "RuntimeBoot",
    "SILENCE_PEAK_THRESHOLD",
    "VAD_FRAME_MS",
    "VAD_RMS_THRESHOLD",
    "WORKSPACE_DIRNAME",
    "boot_runtime",
]
