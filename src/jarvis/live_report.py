from __future__ import annotations

"""Report shapes and EVERY word the live loop prints.

One owner for labeling, so an honest label cannot drift between the code that
did the work and the code that reports it: the mission's stage lines, the
per-step and per-attempt lines, the per-step capability lines, the recovery and
completion lines, the voice-turn lines, and the component listing all come from
here. Callers (the composition root in `jarvis.live`) hand over the values they
measured; they never assemble the wording themselves.

The labels this module must keep honest:

* a stage is `real - ...` only when the real component did the work, and
  `seam - ...` (with the reason) when a declared capability could not be served,
* a step line names its worker, its exit code, its handle and its containment, or
  that a worker failed, so a local in-process write is never read as a dispatch,
* `capability: ...` carries the `CapabilityDatum` label verbatim (see
  `jarvis.live_capability`), and the component listing states how many declared
  step needs a skill really served rather than implying all of them.

Nothing here imports the dispatch seam: records and ladder acts are read by
attribute, so a report line can never depend on how the work was run.
"""

import os
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .live_capability import CapabilityDatum
from .supervisor import RecoveryAction


@dataclass(frozen=True)
class MissionReport:
    mission_id: str
    goal: str
    outcome: str
    steps: tuple[Any, ...]
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


# ---------------------------------------------------------------------------
# mission stage lines
# ---------------------------------------------------------------------------


def intake_line(mission_id: str, goal: str) -> str:
    return f"intake: mission {mission_id} started on stream 'mission' (goal={goal!r})"


def decompose_line(step_ids: Sequence[str]) -> str:
    return "decompose: " + " -> ".join(step_ids)


def router_line(implemented: str | None, verifier: str | None, i5_ok: bool) -> str:
    return (
        "router: implementation.v1 -> "
        f"{implemented or 'none'}; verification.v1 -> "
        f"{verifier or 'none'}; red-team -> freebuff; "
        + ("invariant I5 HOLDS" if i5_ok else "invariant I5 VIOLATED - verification refused")
    )


def worker_summary(worker_note: str, engine: str) -> str:
    return f"{worker_note}; engine: {engine}"


def worker_line(worker_note: str, engine: str) -> str:
    return f"worker: {worker_summary(worker_note, engine)}"


def verifier_summary(provider: str, instance_id: str, excluded: Iterable[str]) -> str:
    return (
        f"provider {provider!r}, fresh process per attempt, "
        f"instance {instance_id}, I5 exclusion set {sorted(excluded)}"
    )


def verifier_line(provider: str, instance_id: str, excluded: Iterable[str]) -> str:
    return (
        f"verifier: provider {provider!r}, fresh process per attempt, "
        f"instance {instance_id}; I5 exclusion set {sorted(excluded)}"
    )


def verifier_component_label(provider: str, instance_id: str) -> str:
    return (
        f"provider {provider!r}, fresh process per attempt "
        f"(instance {instance_id})"
    )


def dispatch_label(external_attempt_count: int) -> str:
    """What really happened on the worker side: a dispatch, or a local fallback."""
    if external_attempt_count:
        return (
            f"real - {external_attempt_count} attempt(s) spawned through an L7 bridge "
            "with preconditions, containment and a real handle"
        )
    return (
        "preconditions validated per step, but NO external process was spawned "
        "(the worker is local; see --worker external)"
    )


def i5_refusal_line(provider: str) -> str:
    return (
        "I5: verification refused - the only provider available for "
        f"verification.v1 is {provider!r}, which already red-teamed "
        "this package; the mission HOLDS"
    )


def step_line(record: Any) -> str:
    """One step attempt: the verdict, its recovery, and WHO really ran it."""
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
    return (
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


def capability_line(datum: CapabilityDatum) -> str:
    """The per-step capability label, verbatim from the datum (never re-worded)."""
    return f"capability: {datum.label}"


# ---------------------------------------------------------------------------
# recovery, completion, recall, daemon lines
# ---------------------------------------------------------------------------


def recovery_action_line(act: Any) -> str:
    """One ladder action, with a declared-but-unexecuted seam named as such."""
    if act.action is RecoveryAction.ROLLBACK:
        return (
            "recover: ROLLBACK declared to "
            f"{act.rolled_back_to or 'last-known-good'}; git seam NOT injected "
            "- declared, not executed"
        )
    if act.action is RecoveryAction.ESCALATE and act.escalation is not None:
        return (
            "recover: ESCALATE bundle -> step "
            f"{act.escalation.step_id}, attempts {act.escalation.attempts_used}, "
            f"reason {act.escalation.reason!r}, failure bytes carried"
        )
    return f"recover: {act.action.value.upper()} - {act.reason}"


def completion_line(passed: bool, event_type: str, lifecycle_state: str) -> str:
    return (
        f"completion: gate {'PASSED' if passed else 'REFUSED'} -> "
        f"{event_type}; mission lifecycle state={lifecycle_state}"
    )


def recovery_halt_line(outcome: str, act: Any) -> str:
    return (
        f"recover: mission halted with {outcome}; ladder action "
        f"{act.action.value} materialized for step {act.step.id}"
    )


def recovery_materialized_line(acts: Sequence[Any]) -> str:
    actions = ", ".join(f"{act.action.value} on {act.step.id}" for act in acts)
    return (
        f"recover: {len(acts)} ladder action(s) materialized ({actions}); "
        "every step still reached FROZEN_SUCCESS"
    )


def recovery_none_line() -> str:
    return "recover: ladder consulted, no failure, no action needed"


def recall_line(written_status: str, hits: Sequence[Any], goal: str) -> str:
    return (
        f"recall: memory {written_status}; {len(hits)} hit(s) for {goal!r}"
        + (f"; top={hits[0].content[:60]!r} score={hits[0].score}" if hits else "")
    )


def daemon_line(daemon: str) -> str:
    return f"daemon: {daemon}"


# ---------------------------------------------------------------------------
# the component listing
# ---------------------------------------------------------------------------


def capability_component_label(datums: Sequence[CapabilityDatum], held: str) -> str:
    """What the capability fabric actually did in this run (or did not).

    Per step: the skill that produced that step's declared datum, or that a
    seam did (whose reason is printed with the step). Counts are stated, not
    implied, so a run that resolved one need of three cannot read as three.
    """
    if not datums:
        return "constructed but not exercised by this command"
    latest: dict[str, CapabilityDatum] = {}
    for datum in datums:
        latest[datum.step_id] = datum
    produced = [
        f"{step_id}->{datum.skill_id}"
        for step_id, datum in sorted(latest.items())
        if datum.skill_id
    ]
    seams = sorted(step_id for step_id, datum in latest.items() if not datum.skill_id)
    summary = (
        f"{len(produced)} of {len(latest)} declared step needs produced by skills "
        f"({', '.join(produced)})"
        if produced
        else f"none of {len(latest)} declared step needs produced by skills"
    )
    if seams:
        summary += f"; seams: {', '.join(seams)} (reason printed per step)"
    if produced:
        summary += "; every skill answer recomputed by the fresh-process verifier"
    return f"{summary}; {held}"


def daemon_status_label(lease_count: int) -> str:
    return (
        f"real - {lease_count} lease(s) and the dispatch journal adjudicated by "
        "SupervisorDaemon.run_tick (effects seam NOT injected: decision plane only)"
    )


def gateway_label(*, configured: bool, answer_path: str | None) -> str:
    if not configured:
        return "offline - no model backend configured; deterministic recall answers"
    if answer_path is not None:
        return f"configured via env; this turn: {answer_path}"
    return "configured via env - not called by this command"


def components_lines(
    *,
    mission: bool,
    log_path: str,
    projection_digest: str,
    provider_count: int,
    workspace: str,
    manifest_id: str,
    step_count: Any,
    capability_label: str,
    worker_label: str,
    verifier_label: str,
    binaries: Mapping[str, bool],
    daemon_status: str,
    stt_engine: str,
    tts_engine: str,
    gateway: str,
) -> tuple[str, ...]:
    """The per-component listing: what is real, what is a seam, what is unwired."""
    lines = [
        f"memory kernel: real - EventLog {log_path} hash-chained, projection "
        f"digest {projection_digest[:16]}, {provider_count} seeded providers",
    ]
    if mission:
        lines += [
            f"effect envelope + fs adapter: real - workspace jail {workspace}, "
            "atomic write, postcondition verify before the effect counts",
            "manifest: real - kernel validate_proposal -> Manifest "
            f"{manifest_id[:12] or 'n/a'} declaring fs.write",
            "orchestrator router (L5): real - roles resolved on canonical identities with "
            "the I5 exclusion applied",
            "orchestrator mission fold (M3.2): real - MissionRunner ratchet over "
            f"{step_count or 'n/a'} declared steps",
            "capability fabric (spec 20): " + capability_label,
            "orchestrator recovery (M3.4): real ladder + ACT; git rollback seam NOT "
            "injected (ROLLBACK declared, never executed)",
            f"worker: {worker_label}",
            f"verifier: {verifier_label}",
            "orchestrator bridges (L7): constructed; engine binaries present: "
            f"{dict(binaries)}; a local worker is never reported as a dispatch",
            f"supervisor daemon (M3.5): {daemon_status}",
            "recall: real - MemoryIndex fold over the same hash-chained log",
        ]
    else:
        lines += [
            "orchestrator (L5/L7/M3.2/M3.4/M3.5): constructed at runtime init, not "
            "exercised by a voice turn",
            "recall: real - deterministic lexical recall over committed memory",
        ]
    lines += [
        f"stt: {stt_engine}",
        f"tts: {tts_engine}",
        "vision: NOT wired - VisionModelAdapter stays library-only; no image turn exists "
        "in this loop",
        f"model gateway: {gateway}",
    ]
    return tuple(lines)


# ---------------------------------------------------------------------------
# voice-turn lines
# ---------------------------------------------------------------------------


def stt_seam_line(engine: str, audio_name: str) -> str:
    return (
        f"stt: seam - {engine}; audio {audio_name} was NOT transcribed "
        "(no mock transcript is fabricated)"
    )


def stt_transcribed_line(engine: str, transcript: str) -> str:
    return f"stt: {engine} -> {transcript[:80]!r}"


def stt_typed_line(engine: str) -> str:
    return (
        f"stt: {engine} (no audio supplied; transcript taken from the "
        "spoken text argument, nothing was transcribed)"
    )


def vad_real_line(
    *,
    frame_count: int,
    frame_ms: int,
    audio_name: str,
    speech_frames: int,
    rms_threshold: float,
) -> str:
    return (
        f"real - {frame_count} frames @{frame_ms}ms of the real samples in "
        f"{audio_name} ({speech_frames} speech / "
        f"{frame_count - speech_frames} silence at RMS > {rms_threshold}); "
        "the FSM's collected buffer holds those bytes, not a placeholder"
    )


def vad_line(vad: str) -> str:
    return f"vad: {vad}"


def vad_declared_line() -> str:
    return (
        "caller-declared - no audio frames could be read, so the typed text "
        "drives the FSM (no microphone was opened; nothing was captured)"
    )


def tts_skipped_line(engine: str) -> str:
    return f"tts: skipped - nothing to speak ({engine})"


def tts_seam_line(engine: str) -> str:
    return f"tts: {engine}"


def tts_failed_line(engine: str, error: BaseException) -> str:
    return (
        f"tts: {engine} FAILED ({type(error).__name__}: {error}); NO audio "
        "was produced - a resolved TTS engine must write a real, non-silent WAV"
    )


def tts_wrote_line(engine: str, target: str, facts: Mapping[str, Any], byte_count: int) -> str:
    return (
        f"tts: {engine} -> wrote {target} "
        f"({facts['duration_seconds']:.2f}s of speech, {facts['sample_rate']} Hz, "
        f"peak {facts['peak']:.3f} / RMS {facts['rms']:.4f}, {byte_count} bytes, "
        "measured non-silent)"
    )


def voice_loop_line(states: Sequence[str]) -> str:
    return (
        "voice loop: real 6-state turn-taking FSM; transitions journaled on stream "
        f"'voice-session' ({' -> '.join(states)})"
    )


def answer_line(
    *, answered: bool, answer: str, used_model: bool, provider_id: str, confidence: float
) -> str:
    return (
        "answer: "
        + (f"{answer!r}" if answered else "no relevant memory (deterministic offline path)")
        + (
            f" (model-grounded via {provider_id})"
            if used_model
            else f" (confidence {confidence:.2f})"
        )
    )


def voice_answer_path(used_model: bool, provider_id: str) -> str:
    """How the voice answer was really produced, for the component listing."""
    if used_model:
        return f"model-grounded via {provider_id}"
    return "deterministic offline recall (the gateway was not used)"


def model_backend_configured() -> bool:
    """Whether a model backend is configured by the environment (no call made)."""
    return bool(os.environ.get("JARVIS_MODEL_API_KEY"))


__all__ = [
    "MissionReport",
    "VoiceTurnReport",
    "answer_line",
    "capability_component_label",
    "capability_line",
    "completion_line",
    "components_lines",
    "daemon_line",
    "daemon_status_label",
    "decompose_line",
    "dispatch_label",
    "gateway_label",
    "i5_refusal_line",
    "intake_line",
    "model_backend_configured",
    "recall_line",
    "recovery_action_line",
    "recovery_halt_line",
    "recovery_materialized_line",
    "recovery_none_line",
    "router_line",
    "step_line",
    "stt_seam_line",
    "stt_transcribed_line",
    "stt_typed_line",
    "tts_failed_line",
    "tts_seam_line",
    "tts_skipped_line",
    "tts_wrote_line",
    "vad_declared_line",
    "vad_line",
    "vad_real_line",
    "verifier_component_label",
    "verifier_line",
    "verifier_summary",
    "voice_answer_path",
    "voice_loop_line",
    "worker_line",
    "worker_summary",
]
