from __future__ import annotations

"""Composition root + live loop (the missing wiring, additive module).

Everything above M1 shipped as importable, unit-tested folds with no caller:
nothing constructed `MissionRunner`, `Router`, `RecoveryEngine` or
`SupervisorDaemon`, and nothing imported `jarvis.multimodal`. This module is
that caller and nothing else: it constructs the existing components from real
configuration and runs one goal and one voice turn through them.

    intake -> decompose -> dispatch -> verify -> recover -> recall

What is REAL on this path, stated so no claim outruns the disk:

* memory kernel - `CoreService`: creator identity, hash-chained `EventLog`,
  `MemoryProjection`, seeded registry.
* effect + filesystem - `EffectEnvelopeEngine` over the path-jailed
  `FilesystemEffectAdapter`: every artifact is written atomically inside the
  workspace jail and verified by declared postconditions before it counts.
* mission fold - `MissionLifecycleOwner` (M3.1) folds the mission slice, and
  `CompletionGate` (NAT-05) is the ONLY thing that may emit `task.completed`.
* orchestrator - `Router` resolves the L5 roles on canonical identities (I5
  exclusion applied), `MissionRunner` folds the step ratchet, `RecoveryEngine`
  materializes the ladder action, `SupervisorDaemon` adjudicates the real
  dispatch records and the real mission lease.
* voice - `StreamingVoiceLoop` runs the real turn-taking FSM and journals every
  transition; STT/TTS run a real engine ONLY when this machine has one bound
  (`JARVIS_STT_CMD` / `faster-whisper` / `whisper` CLI; `JARVIS_TTS_CMD` /
  `piper` / the Windows OS engine `System.Speech` / `espeak-ng`). With no engine
  bound the adapters are NOT constructed and the turn says `seam` - the M4
  adapters' deterministic default runners are never fed to a user as if they
  were perception. Synthesis is MEASURED before it counts: the WAV is parsed and
  a silent or missing payload is reported as a failed synthesis (the same
  posture the mission side takes on `exit 0` with no artifact), and when a real
  audio file is supplied the FSM is driven by per-frame RMS over the REAL
  samples instead of a caller-declared flag.

The worker/verifier seam lives in `jarvis.live_dispatch`: a real external
worker (`ExternalWorker`, spawned through an existing L7 bridge with
dispatch preconditions, containment, timeout and process-tree kill), a labeled
local fallback that is never called a dispatch, and an `IndependentVerifier`
that adjudicates from a FRESH process attributed to a different provider
(Invariant I5 enforced, not asserted).

Seams that stay open and are named in the output, never hidden: the recovery
git seam is not injected (ROLLBACK is declared, never executed), the local
fallback worker is reported as `local (NOT a dispatch)`, a typed turn declares
that nothing was captured from a device (no microphone is opened), and vision
stays unwired.

Engine reality measured on this machine (2026-09-24), reported rather than
dressed up: `opencode run` never responds non-interactively (killed at
200-240s, empty output, no artifact) and `agy -p` completes but every tool
call is blocked by a malformed hook in the user's global plugin config, so
neither can produce an artifact here. `--worker external` performs the real
dispatch and reports exactly what happened.

Additive law: this module lives outside every frozen package and imports them
read-only.
"""

import asyncio
import io
import json
import os
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .bootstrap import CoreService
from .effects.filesystem import FilesystemEffectAdapter, FilesystemSandbox
from .kernel.done_gate import CompletionGate
from .kernel.effect_envelope import EffectFailure, EffectEnvelope
from .kernel.event_log import Event, EventLog, new_ulid
from .kernel.intent import (
    ContractProposal,
    ContractSeed,
    ValidationFailure,
    validate_proposal,
)
from .kernel.memory_api import Memory
from .kernel.memory_projection import MemoryProjection
from .kernel.memory_write import MemoryWriter
from .kernel.mission_lifecycle import (
    MISSION_STARTED,
    MISSION_STREAM_ID,
    MissionLifecycleOwner,
)
from .kernel.registry import CREATOR_PRINCIPAL_ID, CapabilityRegistry
from .multimodal.streaming import StreamingVoiceLoop
from .multimodal.voice import PiperTTSAdapter, WhisperSTTAdapter
from .live_dispatch import (
    BRIDGE_BINARIES,
    ExternalWorker,
    IndependentVerifier,
    LocalWorker,
    StepOrchestrator,
    StepRecord,
    select_worker,
    step_expectations,
    step_payload,
)
from .orchestrator import AgyBridge, DeepSeekBridge, OpenCodeBridge
from .orchestrator.daemon import Lease, SupervisorDaemon
from .orchestrator.mission_runner import MissionPlan, MissionRunner, MissionStep
from .orchestrator.recovery_engine import RecoveryEngine, RecoveryOutcome
from .orchestrator.router import (
    Role,
    RoleAssignment,
    Router,
    canonical_package,
    canonical_provider,
)
from .supervisor import RecoveryAction, RecoveryPolicy

WORKSPACE_DIRNAME = "workspace"
WORK_ORDER_DIRNAME = "work_orders"
ARTIFACT_DIRNAME = "artifacts"
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
# reports
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MissionReport:
    mission_id: str
    goal: str
    outcome: str
    steps: tuple[StepRecord, ...]
    artifacts: tuple[str, ...]
    lifecycle: str
    completion: str
    recall_hits: int
    digest: str
    dispatch: str
    daemon: str
    worker: str
    verifier: str
    lines: tuple[str, ...]
    components: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return self.outcome == "ACCEPTED"


@dataclass(frozen=True)
class VoiceTurnReport:
    utterance: str
    transcript_source: str
    stt: str
    answered: bool
    answer: str
    confidence: float
    used_model: bool
    tts: str
    audio_out: str | None
    states: tuple[str, ...]
    lines: tuple[str, ...]
    components: tuple[str, ...]
    vad: str = ""
    audio_seconds: float = 0.0
    audio_sample_rate: int = 0
    audio_peak: float = 0.0
    audio_non_silent: bool = False


# The worker / verifier seam lives in `jarvis.live_dispatch` (a real external
# worker, a labeled local fallback, a fresh-process independent verifier and
# the orchestrator that keeps the worker from supplying its own verdict).


class _LocalDecomposer:
    """The declared decomposition seam (M3.2 `Decomposer`): deterministic and
    local. The plan is ordered; the runner folds it, it never folds itself."""

    def decompose(self, goal: str) -> tuple[MissionStep, ...]:
        return (
            MissionStep(id="plan", summary=f"write the mission work order for {goal!r}"),
            MissionStep(id="deliver", summary="write the mission deliverable artifact"),
            MissionStep(id="attest", summary="content-address the deliverable on disk"),
        )


# ---------------------------------------------------------------------------
# the composition root
# ---------------------------------------------------------------------------


class LiveRuntime:
    """Constructs the kernel, orchestrator and multimodal seam; runs them."""

    def __init__(self, service: CoreService, *, supervisor_instance_id: str | None = None) -> None:
        self.service = service
        self.home = service.home
        self.log: EventLog = service.log  # type: ignore[assignment]
        self.workspace = self.home / WORKSPACE_DIRNAME
        # The jail root must exist before ANY dispatch: an external worker is
        # spawned with cwd=workspace, and a missing directory fails the spawn.
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.sandbox = FilesystemSandbox(self.workspace)
        self.adapters: dict[str, Any] = {"fs.default": FilesystemEffectAdapter(self.sandbox)}
        # Live catalog is in-memory (log=None): registering the live providers
        # appends NOTHING, so the §127.1 "4 providers" projection stays intact.
        self.catalog = CapabilityRegistry.seed_m1_defaults()
        self.router = Router()
        self.recovery = RecoveryEngine(policy=RecoveryPolicy(), git=None, package="live-loop")
        self.assignments: list[RoleAssignment] = []
        self.supervisor_id = supervisor_instance_id or (
            "sup-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        )
        self.daemon = SupervisorDaemon(
            heartbeat_stale_after=LEASE_TTL_SECONDS,
            current_supervisor_instance_id=self.supervisor_id,
        )
        self.bridges = {
            "bigpickle": OpenCodeBridge(),
            "freebuff": DeepSeekBridge(),
            "antigravity": AgyBridge(),
        }
        self.stt_runner, self.stt_engine = _resolve_stt_engine()
        self.tts_runner, self.tts_engine = _resolve_tts_engine()
        self.stt = WhisperSTTAdapter(runner=self.stt_runner) if self.stt_runner else None
        self.tts = PiperTTSAdapter(runner=self.tts_runner) if self.tts_runner else None
        self._dispatch_path = self.home / "dispatches.jsonl"
        self.leases: list[Lease] = []
        self._leases_path = self.home / "leases.jsonl"
        self._step_ids: tuple[str, ...] = ()
        self._manifest_id = ""
        self._owner: MissionLifecycleOwner | None = None

    # -- shared internals --------------------------------------------------

    @staticmethod
    def _now() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _deliverable_digest(self, mission_id: str) -> str:
        """sha256 of the deliverable currently on disk (empty when absent)."""
        try:
            return self.sandbox.read_file(f"{ARTIFACT_DIRNAME}/{mission_id}.json")["sha256"]
        except Exception:
            return ""

    def _record_dispatch(self, step_id: str, event: str, *, worker: str) -> str:
        dispatch_id = f"dispatch-{step_id}"
        record = {
            "event": f"DISPATCH_{event}",
            "dispatch_id": dispatch_id,
            "step_id": step_id,
            "worker_id": worker,
            "supervisor_instance_id": self.supervisor_id,
            "ts": time.time(),
        }
        with self._dispatch_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return dispatch_id

    def _write_artifact(
        self,
        *,
        mission_id: str,
        step_id: str,
        attempt: int,
        relative: str,
        content: str,
    ) -> str | None:
        """One real effect through the envelope; returns an error string on refusal."""
        assert self._owner is not None, "run_goal must set the mission owner"
        engine = self._owner.build_effect_engine(self.catalog, self.adapters)
        proposal = ContractProposal(
            contracts=[
                ContractSeed(
                    id="fs.write", version_constraint="1.0.0", args={"path": relative}
                )
            ],
            required_capabilities=["fs.write"],
            intent_id=mission_id,
        )
        manifest = validate_proposal(proposal, self.catalog, ["fs.write"])
        if isinstance(manifest, ValidationFailure):
            return f"manifest rejected: {manifest.reason}: {manifest.detail}"
        self._manifest_id = manifest.manifest_id
        result = asyncio.run(
            engine.run(
                manifest,
                "fs.write",
                intended_change={"path": relative, "requested_capabilities": ["fs.write"]},
                postconditions={"ok": True},
                capability_args={"path": relative, "content": content},
                idempotency_key=f"{mission_id}:{step_id}:{attempt}",
            )
        )
        if isinstance(result, EffectFailure):
            return f"effect {result.reason} in phase {result.phase}: {result.detail}"
        assert isinstance(result, EffectEnvelope)
        return None

    def _write_lease(self, mission_id: str) -> Lease:
        now = time.time()
        lease = Lease(
            lease_id=f"lease-{mission_id}",
            task_id=mission_id,
            worker_id="live-loop",
            supervisor_instance_id=self.supervisor_id,
            expires_at=now + LEASE_TTL_SECONDS,
            renewed_at=now,
        )
        with self._leases_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "lease_id": lease.lease_id,
                        "task_id": lease.task_id,
                        "worker_id": lease.worker_id,
                        "supervisor_instance_id": lease.supervisor_instance_id,
                        "expires_at": lease.expires_at,
                        "renewed_at": lease.renewed_at,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
        self.leases.append(lease)
        return lease

    def _daemon_tick(self) -> str:
        records: list[dict] = []
        if self._dispatch_path.exists():
            for line in self._dispatch_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    records.append(json.loads(line))
        report = self.daemon.run_tick(records, self.leases, now=time.time())
        modes = ",".join(f"{d.trace.dispatch_id}:{d.mode.value}" for d in report.decisions)
        verdicts = ",".join(f"{v.lease.lease_id}:{v.state.value}" for v in report.lease_verdicts)
        return (
            f"real - tick over {len(records)} dispatch records and "
            f"{len(report.lease_verdicts)} lease(s); leases [{verdicts}]; "
            f"dispatches [{modes or 'none'}]"
        )

    # -- the goal: intake -> decompose -> dispatch -> verify -> recover -> recall

    def run_goal(
        self,
        goal: str,
        *,
        faults: Mapping[str, int] | None = None,
        worker_mode: str = "local",
        worker_provider: str | None = None,
        worker_timeout: float = 120.0,
        verifier_timeout: float = 120.0,
    ) -> MissionReport:
        if not goal or not goal.strip():
            raise LiveError("a goal is required")
        goal = goal.strip()
        mission_id = f"mission-{new_ulid()}"
        lines: list[str] = []

        # intake: real durable event on the mission stream
        self.log.append(
            Event(
                stream_id=MISSION_STREAM_ID,
                event_type=MISSION_STARTED,
                principal_id=CREATOR_PRINCIPAL_ID,
                mission_id=mission_id,
                payload={"intent": goal},
            )
        )
        self._owner = MissionLifecycleOwner(self.log, mission_id=mission_id)
        self._owner.advance()
        self._write_lease(mission_id)
        lines.append(f"intake: mission {mission_id} started on stream 'mission' (goal={goal!r})")

        # decompose (declared seam, local and ordered)
        decomposer = _LocalDecomposer()
        steps = decomposer.decompose(goal)
        self._step_ids = tuple(step.id for step in steps)
        lines.append("decompose: " + " -> ".join(self._step_ids))

        # L5 router: resolve the pipeline roles on canonical identities, then
        # ENFORCE Invariant I5 (fail-closed) instead of asserting it.
        self.assignments.append(
            RoleAssignment(package=mission_id, role=Role.RED_TEAM_REVIEWER, provider="freebuff")
        )
        implemented = self.router.resolve(Role.IMPLEMENTER, mission_id, self.assignments)
        resolved_verifier = self.router.resolve(
            Role.INDEPENDENT_VERIFIER, mission_id, self.assignments
        )
        excluded = frozenset(
            canonical_provider(assignment.provider)
            for assignment in self.assignments
            if assignment.role is Role.RED_TEAM_REVIEWER
            and canonical_package(assignment.package) == canonical_package(mission_id)
        )
        worker_provider = worker_provider or implemented.provider or "bigpickle"
        verifier_provider = resolved_verifier.provider or "antigravity"
        i5_ok = (
            implemented.provider is not None
            and resolved_verifier.provider is not None
            and canonical_provider(verifier_provider) not in excluded
        )
        lines.append(
            "router: implementation.v1 -> "
            f"{implemented.provider or 'none'}; verification.v1 -> "
            f"{resolved_verifier.provider or 'none'}; red-team -> freebuff; "
            + ("invariant I5 HOLDS" if i5_ok else "invariant I5 VIOLATED - verification refused")
        )

        # worker: a real external process through the provider's bridge, or the
        # labeled local fallback. The verifier is a SEPARATE object that runs
        # its check in a fresh process, so no worker supplies its own verdict.
        def _phase(step_id: str, phase: str, engine: str) -> None:
            self._record_dispatch(step_id, phase, worker=engine)

        binary = BRIDGE_BINARIES.get(canonical_provider(worker_provider))
        bridge = self.bridges.get(canonical_provider(worker_provider))
        present = bool(binary and shutil.which(binary))
        local_worker = LocalWorker(self._write_artifact, faults, on_phase=_phase)

        def _external_factory() -> ExternalWorker:
            return ExternalWorker(
                provider=worker_provider,
                binary=binary or "",
                bridge=bridge or OpenCodeBridge(),
                workspace=self.workspace,
                timeout=worker_timeout,
                resolve_jailed=self.sandbox.resolve_jailed,
                on_phase=_phase,
            )

        worker, worker_note = select_worker(
            mode=worker_mode,
            provider=worker_provider,
            bridge=bridge,
            binary=binary,
            binary_present=present,
            local=local_worker,
            external_factory=_external_factory,
        )
        verifier = IndependentVerifier(
            workspace=self.workspace,
            provider=verifier_provider,
            excluded=excluded,
            timeout=verifier_timeout,
        )
        lines.append(f"worker: {worker_note}; engine: {worker.engine}")
        lines.append(
            f"verifier: provider {verifier_provider!r}, fresh process per attempt, "
            f"instance {verifier.instance_id}; I5 exclusion set {sorted(excluded)}"
        )

        orchestrator = StepOrchestrator(
            worker=worker,
            verifier=verifier,
            recovery=self.recovery,
            goal=goal,
            mission_id=mission_id,
            step_ids=self._step_ids,
            payload=lambda step, attempt, carried: step_payload(
                step,
                mission_id=mission_id,
                goal=goal,
                step_ids=self._step_ids,
                attempt=attempt,
                carried=carried,
                deliverable_digest=self._deliverable_digest(mission_id),
            ),
            expectations=lambda step: step_expectations(
                step.id,
                mission_id=mission_id,
                goal=goal,
                step_ids=self._step_ids,
                deliverable=f"{ARTIFACT_DIRNAME}/{mission_id}.json",
            ),
            now=self._now,
        )

        if i5_ok:
            run = MissionRunner().run(
                plan=MissionPlan.declared(plan_id=mission_id, steps=steps),
                verifier=orchestrator,
                observed_at=self._now(),
            )
            outcome = run.outcome
            records = orchestrator.records
            acts = orchestrator.acts
        else:
            outcome = "HELD"
            records = []
            acts = []
            lines.append(
                "I5: verification refused - the only provider available for "
                f"verification.v1 is {verifier_provider!r}, which already red-teamed "
                "this package; the mission HOLDS"
            )

        for record in records:
            verdict = "verified" if record.verified else f"FAILED ({record.verification})"
            if record.external:
                detail = (
                    f"; worker {record.worker_engine} pid={record.worker_pid} "
                    f"exit={record.worker_exit} handle={record.handle_id}"
                    + (f"; containment {record.containment}" if record.containment else "")
                )
            elif record.worker_error:
                detail = f"; worker error ({record.worker_engine}): {record.worker_error}"
            else:
                detail = ""
            lines.append(
                f"step {record.step_id}: attempt {record.attempt} -> {verdict}"
                + (f"; recovery {record.ladder}" if record.ladder else "")
                + ("; retry context carried" if record.retry_carried else "")
                + detail
                + (
                    f"; verified by {record.verifier} in pid {record.verifier_pid}"
                    if record.verified and record.verifier_pid
                    else ""
                )
            )
        for act in acts:
            if act.action is RecoveryAction.ROLLBACK:
                lines.append(
                    "recover: ROLLBACK declared to "
                    f"{act.rolled_back_to or 'last-known-good'}; git seam NOT injected "
                    "- declared, not executed"
                )
            elif act.action is RecoveryAction.ESCALATE and act.escalation is not None:
                lines.append(
                    "recover: ESCALATE bundle -> step "
                    f"{act.escalation.step_id}, attempts {act.escalation.attempts_used}, "
                    f"reason {act.escalation.reason!r}, failure bytes carried"
                )
            else:
                lines.append(f"recover: {act.action.value.upper()} - {act.reason}")

        artifacts = tuple(record.wrote for record in records if record.wrote is not None)
        # Acceptance is the FINAL attempt of every step being verified - a
        # repaired attempt stays in the record as a real failed attempt.
        final_by_step = {record.step_id: record for record in records}
        accepted = (
            outcome == "ACCEPTED"
            and bool(final_by_step)
            and all(record.verified for record in final_by_step.values())
        )

        # completion: NAT-05 gate is the only writer of task.completed
        gate = CompletionGate(self.log, principal_id=CREATOR_PRINCIPAL_ID)
        if accepted and artifacts:
            decision = gate.declare_completion(
                task_id=mission_id,
                evidence={
                    "artifact": artifacts[-1],
                    "verification": "VERIFIED by an independent fresh verification process",
                },
                mission_id=mission_id,
            )
        else:
            decision = gate.declare_completion(
                task_id=mission_id,
                evidence={"artifact": "", "verification": ""},
                mission_id=mission_id,
            )
        state, _ = self._owner.advance()
        event_type = "task.completed" if decision.passed else "task.completion_refused"
        completion = "completed" if decision.passed else "refused"
        lines.append(
            f"completion: gate {'PASSED' if decision.passed else 'REFUSED'} -> "
            f"{event_type}; mission lifecycle state={state.state}"
        )

        # recover: the ladder decided, the ACT plane materialized
        if not accepted and acts:
            act = acts[-1]
            lines.append(
                f"recover: mission halted with {outcome}; ladder action "
                f"{act.action.value} materialized for step {act.step.id}"
            )
        elif acts:
            actions = ", ".join(f"{act.action.value} on {act.step.id}" for act in acts)
            lines.append(
                f"recover: {len(acts)} ladder action(s) materialized ({actions}); "
                "every step still reached FROZEN_SUCCESS"
            )
        else:
            lines.append("recover: ladder consulted, no failure, no action needed")

        # recall: write the outcome into memory, then read it back
        memory_note = (
            f"mission {mission_id} {completion} the goal {goal!r}; "
            f"{len(records)} step attempts, outcome {outcome}"
        )
        written = MemoryWriter(self.log).remember(
            content=memory_note, source=f"mission {mission_id}"
        )
        hits = Memory(log=self.log).recall(goal, limit=3)
        lines.append(
            f"recall: memory {written.status}; {len(hits)} hit(s) for {goal!r}"
            + (f"; top={hits[0].content[:60]!r} score={hits[0].score}" if hits else "")
        )

        daemon = self._daemon_tick()
        lines.append(f"daemon: {daemon}")
        # Rebuilt from the log: `CoreService.projection()` is the boot-time
        # snapshot and would under-report after this run's appends.
        projection = MemoryProjection.rebuild(self.log)
        external_attempts = [r for r in records if r.external]
        report = MissionReport(
            mission_id=mission_id,
            goal=goal,
            outcome=outcome,
            steps=tuple(records),
            artifacts=artifacts,
            lifecycle=state.state,
            completion=completion,
            recall_hits=len(hits),
            digest=projection.digest(),
            dispatch=(
                f"real - {len(external_attempts)} attempt(s) spawned through an L7 bridge "
                "with preconditions, containment and a real handle"
                if external_attempts
                else "preconditions validated per step, but NO external process was spawned "
                "(the worker is local; see --worker external)"
            ),
            daemon=daemon,
            worker=f"{worker_note}; engine: {worker.engine}",
            verifier=(
                f"provider {verifier_provider!r}, fresh process per attempt, "
                f"instance {verifier.instance_id}, I5 exclusion set {sorted(excluded)}"
            ),
            lines=tuple(lines),
            components=self.components(
                mission=True,
                worker_label=f"{worker_note}; engine: {worker.engine}",
                verifier_label=(
                    f"provider {verifier_provider!r}, fresh process per attempt "
                    f"(instance {verifier.instance_id})"
                ),
            ),
        )
        return report

    # -- the voice turn ----------------------------------------------------

    def voice_turn(
        self,
        utterance: str,
        *,
        audio: Path | str | None = None,
        answerer: Callable[[str], Any] | None = None,
    ) -> VoiceTurnReport:
        lines: list[str] = []
        transcript = (utterance or "").strip()
        source = "typed utterance"
        frames: list[tuple[bytes, bool]] | None = None

        if audio is not None:
            path = Path(audio)
            try:
                raw_audio = path.read_bytes()
            except OSError:
                raw_audio = b""
            # real frames, real per-frame energy: the FSM is fed the samples
            frames = _wav_vad_frames(raw_audio) if raw_audio else None
            if self.stt is None:
                lines.append(
                    f"stt: seam - {self.stt_engine}; audio {path.name} was NOT transcribed "
                    "(no mock transcript is fabricated)"
                )
            else:
                spoken = asyncio.run(
                    self.stt.invoke(
                        "audio.transcribe",
                        "1.0.0",
                        {"audio_path": str(path), "format": path.suffix.lstrip(".") or "wav"},
                    )
                )
                transcript = spoken["text"]
                source = f"transcribed from {path.name} by {spoken.get('engine', 'engine')}"
                lines.append(f"stt: {self.stt_engine} -> {transcript[:80]!r}")
        else:
            lines.append(
                f"stt: {self.stt_engine} (no audio supplied; transcript taken from the "
                "spoken text argument, nothing was transcribed)"
            )

        # the real turn-taking FSM: every transition is a real audit event
        states: list[str] = []
        loop = StreamingVoiceLoop(
            event_log=self.log,
            on_state_change=lambda _old, new: states.append(new.value),
        )
        loop.start_listening()
        if frames:
            speech_frames = sum(1 for _frame, active in frames if active)
            for frame, active in frames:
                loop.feed_audio_frame(frame, vad_active=active)
            vad = (
                f"real - {len(frames)} frames @{VAD_FRAME_MS}ms of the real samples in "
                f"{Path(audio).name} ({speech_frames} speech / "
                f"{len(frames) - speech_frames} silence at RMS > {VAD_RMS_THRESHOLD}); "
                "the FSM's collected buffer holds those bytes, not a placeholder"
            )
        else:
            # no frames to measure: say so instead of implying a capture
            loop.feed_audio_frame(b"", vad_active=bool(transcript))
            vad = (
                "caller-declared - no audio frames could be read, so the typed text "
                "drives the FSM (no microphone was opened; nothing was captured)"
            )
        for _ in range(loop.silence_threshold_frames):
            loop.feed_audio_frame(b"", vad_active=False)

        result = (
            answerer(transcript)
            if answerer is not None
            else _offline_answer(self.service.projection(), transcript)
        )
        answered = bool(getattr(result, "answered", False))
        answer = getattr(result, "answer", "") if answered else ""
        loop.start_assistant_speaking()

        audio_out: str | None = None
        audio_seconds = 0.0
        audio_rate = 0
        audio_peak = 0.0
        audio_non_silent = False
        if not answered:
            lines.append(f"tts: skipped - nothing to speak ({self.tts_engine})")
        elif self.tts is None:
            lines.append(f"tts: {self.tts_engine}")
        else:
            try:
                spoken_out = asyncio.run(
                    self.tts.invoke(
                        "audio.synthesize", "1.0.0", {"text": answer, "format": "wav"}
                    )
                )
                payload = bytes(spoken_out["audio_bytes"])
                if not payload:
                    raise ValueError("the engine returned no bytes")
                # measured, never assumed: a payload that is not a real WAV, or a
                # WAV that carries only silence, is a FAILED synthesis. Success is
                # not evidence here any more than `exit 0` is on the worker side.
                facts = _wav_facts(payload)
                if not facts["non_silent"]:
                    raise ValueError("the engine wrote a silent WAV (peak is zero)")
            except Exception as exc:  # a synthesis fault is reported, never faked
                lines.append(
                    f"tts: {self.tts_engine} FAILED ({type(exc).__name__}: {exc}); NO audio "
                    "was produced - a resolved TTS engine must write a real, non-silent WAV"
                )
            else:
                target_dir = self.home / AUDIO_DIRNAME
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / f"turn-{new_ulid()}.wav"
                target.write_bytes(payload)
                audio_out = str(target)
                audio_seconds = facts["duration_seconds"]
                audio_rate = facts["sample_rate"]
                audio_peak = facts["peak"]
                audio_non_silent = facts["non_silent"]
                lines.append(
                    f"tts: {self.tts_engine} -> wrote {target} "
                    f"({facts['duration_seconds']:.2f}s of speech, {facts['sample_rate']} Hz, "
                    f"peak {facts['peak']:.3f} / RMS {facts['rms']:.4f}, {len(payload)} bytes, "
                    "measured non-silent)"
                )
        loop.finish_assistant_speaking()

        lines.append(
            "voice loop: real 6-state turn-taking FSM; transitions journaled on stream "
            f"'voice-session' ({' -> '.join(states)})"
        )
        lines.append(f"vad: {vad}")
        lines.append(
            "answer: "
            + (f"{answer!r}" if answered else "no relevant memory (deterministic offline path)")
            + (
                f" (model-grounded via {getattr(result, 'provider_id', 'gateway')})"
                if getattr(result, "used_model", False)
                else f" (confidence {getattr(result, 'confidence', 0.0):.2f})"
            )
        )
        return VoiceTurnReport(
            utterance=transcript,
            transcript_source=source,
            stt=self.stt_engine,
            answered=answered,
            answer=answer,
            confidence=float(getattr(result, "confidence", 0.0)),
            used_model=bool(getattr(result, "used_model", False)),
            tts=self.tts_engine,
            audio_out=audio_out,
            states=tuple(states),
            lines=tuple(lines),
            vad=vad,
            audio_seconds=audio_seconds,
            audio_sample_rate=audio_rate,
            audio_peak=audio_peak,
            audio_non_silent=audio_non_silent,
            components=self.components(
                mission=False,
                answer_path=(
                    f"model-grounded via {getattr(result, 'provider_id', 'gateway')}"
                    if getattr(result, "used_model", False)
                    else "deterministic offline recall (the gateway was not used)"
                ),
            ),
        )

    # -- honest status lines, per component --------------------------------

    def components(
        self,
        *,
        mission: bool,
        answer_path: str | None = None,
        worker_label: str = "not exercised by this command",
        verifier_label: str = "not exercised by this command",
    ) -> tuple[str, ...]:
        projection = MemoryProjection.rebuild(self.log)
        if not os.environ.get("JARVIS_MODEL_API_KEY"):
            gateway = "offline - no model backend configured; deterministic recall answers"
        elif answer_path is not None:
            gateway = f"configured via env; this turn: {answer_path}"
        else:
            gateway = "configured via env - not called by this command"
        binaries = {
            name: bool(shutil.which(binary))
            for name, binary in (("bigpickle", "opencode"), ("antigravity", "agy"))
        }
        lines = [
            f"memory kernel: real - EventLog {self.log_path()} hash-chained, projection "
            f"digest {projection.digest()[:16]}, {len(self.service.provider_ids())} seeded providers",
        ]
        if mission:
            lines += [
                f"effect envelope + fs adapter: real - workspace jail {self.workspace}, "
                "atomic write, postcondition verify before the effect counts",
                "manifest: real - kernel validate_proposal -> Manifest "
                f"{self._manifest_id[:12] or 'n/a'} declaring fs.write",
                "orchestrator router (L5): real - roles resolved on canonical identities with "
                "the I5 exclusion applied",
                "orchestrator mission fold (M3.2): real - MissionRunner ratchet over "
                f"{len(self._step_ids) or 'n/a'} declared steps",
                "orchestrator recovery (M3.4): real ladder + ACT; git rollback seam NOT "
                "injected (ROLLBACK declared, never executed)",
                f"worker: {worker_label}",
                f"verifier: {verifier_label}",
                "orchestrator bridges (L7): constructed; engine binaries present: "
                f"{binaries}; a local worker is never reported as a dispatch",
                f"supervisor daemon (M3.5): {self._daemon_status()}",
                "recall: real - MemoryIndex fold over the same hash-chained log",
            ]
        else:
            lines += [
                "orchestrator (L5/L7/M3.2/M3.4/M3.5): constructed at runtime init, not "
                "exercised by a voice turn",
                "recall: real - deterministic lexical recall over committed memory",
            ]
        lines += [
            f"stt: {self.stt_engine}",
            f"tts: {self.tts_engine}",
            "vision: NOT wired - VisionModelAdapter stays library-only; no image turn exists "
            "in this loop",
            f"model gateway: {gateway}",
        ]
        return tuple(lines)

    def _daemon_status(self) -> str:
        return (
            f"real - {len(self.leases)} lease(s) and the dispatch journal adjudicated by "
            "SupervisorDaemon.run_tick (effects seam NOT injected: decision plane only)"
        )

    def log_path(self) -> str:
        return str(self.service.log_path)


def _offline_answer(projection: Any, question: str) -> Any:
    from .kernel.memory_query import answer

    return answer(projection, question)


__all__ = [
    "LiveError",
    "LiveRuntime",
    "MissionReport",
    "StepRecord",
    "VoiceTurnReport",
]
