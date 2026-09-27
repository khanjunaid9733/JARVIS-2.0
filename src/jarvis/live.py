from __future__ import annotations

"""Composition root + live loop (the missing wiring, additive module).

Everything above M1 shipped as importable, unit-tested folds with no caller:
nothing constructed `MissionRunner`, `Router`, `RecoveryEngine` or
`SupervisorDaemon`, and nothing imported `jarvis.multimodal`. This module is
that caller and nothing else: it constructs the existing components from real
configuration and runs one goal and one voice turn through them.

    intake -> decompose -> dispatch -> verify -> recover -> recall

This file is deliberately COMPOSITION ONLY, so a maintainer can read one concern
at a time; each concern has exactly one owner and one place to change:

* `jarvis.live_boot` - configuration/bootstrap: which engines and components
  really exist on this machine, and the honest `real - ...` / `seam - ...` label
  for each (`boot_runtime`).
* `jarvis.live_steps` - the step model: which steps a mission has, the artifact
  and datum each declares (`step_payload`), what the verifier must find
  (`step_expectations`), and the capability each step's work needs
  (`step_capability`).
* `jarvis.live_dispatch` - dispatch + independent verification: the real external
  worker, the labeled local fallback, the fresh-process `IndependentVerifier`, and
  the orchestrator that keeps a worker from supplying its own verdict.
* `jarvis.live_capability` - capability resolution: ranking the fabric for a
  step's declared need, trying the ranked candidates through the existing
  dispatcher, and turning the outcome into a `real - skill ...` / `seam - ...`
  datum.
* `jarvis.live_report` - report shapes and every printed word: stage lines, step
  and capability lines, recovery/completion/recall lines, voice lines and the
  component listing.
* `jarvis.live_voice` - one spoken turn: STT, the turn-taking FSM, the answer
  path and the measured TTS write (`VoiceTurn`).

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
* voice - `jarvis.live_voice.VoiceTurn` runs one turn: `StreamingVoiceLoop`
  drives the real turn-taking FSM and journals every transition; STT/TTS run a
  real engine ONLY when this machine has one bound
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

The capability fabric (spec §20) is consulted for every STEP, from the step's own
contract: `step_capability` declares the datum a step's work needs (the mission
intent's content-address on `plan` and `deliver`, the deliverable's on `attest`),
`SkillRuntimeEngine` (the existing engine - no second dispatcher, no parallel
registry) ranks the library for that declared query, and the ranked candidates are
tried IN ORDER through the existing dispatcher until one produces a well-formed
datum. Every attempt is audited on this mission's real hash-chained log
(`skill.dispatched` / `skill.succeeded` / `skill.refused` / `skill.failed` all join
to the mission by `mission_id`). `real - skill ...` means a skill in the fabric
produced that step's datum and the fresh-process verifier recomputed it from the
subject bytes, so a wrong answer fails the step; `seam - ...` means no candidate
could, every reason is named, and the deterministic local path produced the datum
instead - never dressed up as a capability.

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
import json
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Mapping

from .bootstrap import CoreService
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
from .kernel.registry import CREATOR_PRINCIPAL_ID
from .live_boot import (
    LEASE_TTL_SECONDS,
    LiveError,
    RuntimeBoot,
    _resolve_stt_engine,
    _resolve_tts_engine,
    boot_runtime,
)
from .live_dispatch import (
    BRIDGE_BINARIES,
    ExternalWorker,
    IndependentVerifier,
    LocalWorker,
    StepOrchestrator,
    StepRecord,
    select_worker,
)
from .live_report import (
    MissionReport,
    VoiceTurnReport,
    capability_component_label,
    capability_line,
    completion_line,
    components_lines,
    daemon_line,
    daemon_status_label,
    decompose_line,
    dispatch_label,
    gateway_label,
    i5_refusal_line,
    intake_line,
    model_backend_configured,
    recall_line,
    recovery_action_line,
    recovery_halt_line,
    recovery_materialized_line,
    recovery_none_line,
    router_line,
    step_line,
    verifier_component_label,
    verifier_line,
    verifier_summary,
    worker_line,
    worker_summary,
)
from .live_steps import (
    ARTIFACT_DIRNAME,
    LocalDecomposer,
    step_expectations,
    step_payload,
)
from .live_voice import VoiceTurn
from .orchestrator import OpenCodeBridge
from .orchestrator.daemon import Lease
from .orchestrator.mission_runner import MissionPlan, MissionRunner, MissionStep
from .orchestrator.router import (
    Role,
    RoleAssignment,
    canonical_package,
    canonical_provider,
)

if TYPE_CHECKING:  # typing only: the fabric is imported on first USE, see below
    from .skills.engine import SkillRuntimeEngine

# Every name this module uses comes from the owner that defines it; there is no
# compatibility re-export surface left (verified: nothing inside this repo - CLI,
# tests, scripts - imported a moved name through `jarvis.live`, and the only
# things imported from here at all are `LiveRuntime` and the two engine
# resolvers used below, which stay bound here on purpose so a caller can rebind
# them without touching the bootstrap).


class LiveRuntime:
    """Constructs the kernel, orchestrator and multimodal seams; runs them.

    Composition only: components come from `jarvis.live_boot`, steps from
    `jarvis.live_steps`, each step's declared capability from
    `jarvis.live_capability`, the worker/verifier from `jarvis.live_dispatch`,
    and every printed word from `jarvis.live_report`.
    """

    def __init__(
        self,
        service: CoreService,
        *,
        supervisor_instance_id: str | None = None,
        skill_engine: SkillRuntimeEngine | None = None,
    ) -> None:
        boot = boot_runtime(
            service,
            supervisor_instance_id=supervisor_instance_id,
            skill_engine=skill_engine,
            resolve_stt=_resolve_stt_engine,
            resolve_tts=_resolve_tts_engine,
        )
        self.boot: RuntimeBoot = boot
        self.service = boot.service
        self.home = boot.home
        self.log: EventLog = boot.log
        self.workspace = boot.workspace
        self.sandbox = boot.sandbox
        self.adapters = boot.adapters
        self.catalog = boot.catalog
        self.router = boot.router
        self.recovery = boot.recovery
        self.supervisor_id = boot.supervisor_id
        self.daemon = boot.daemon
        self.bridges = boot.bridges
        self.stt = boot.stt
        self.stt_engine = boot.stt_engine
        self.tts = boot.tts
        self.tts_engine = boot.tts_engine
        self._dispatch_path = boot.dispatch_path
        self.leases = boot.leases
        self._leases_path = boot.leases_path
        # The capability fabric (spec §20) is built on FIRST USE and every datum
        # it resolves is kept per attempt, so a report can state what really
        # happened (see `jarvis.live_capability`).
        self._capabilities = boot.capabilities
        self.assignments: list[RoleAssignment] = []
        self._step_ids: tuple[str, ...] = ()
        self._manifest_id = ""
        self._owner: MissionLifecycleOwner | None = None
        # The voice turn is its own owner (`jarvis.live_voice`); the offline answer
        # path and the component listing this runtime owns are handed to it.
        self._voice = VoiceTurn(
            log=self.log,
            home=self.home,
            stt=self.stt,
            stt_engine=self.stt_engine,
            tts=self.tts,
            tts_engine=self.tts_engine,
            offline_answer=lambda question: _offline_answer(
                self.service.projection(), question
            ),
            components=self.components,
        )

    # -- shared internals --------------------------------------------------

    @staticmethod
    def _now() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

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
        lines.append(intake_line(mission_id, goal))

        # decompose (declared seam, local and ordered)
        decomposer = LocalDecomposer()
        steps = decomposer.decompose(goal)
        self._step_ids = tuple(step.id for step in steps)
        lines.append(decompose_line(self._step_ids))

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
        lines.append(router_line(implemented.provider, resolved_verifier.provider, i5_ok))

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
        worker_label = worker_summary(worker_note, worker.engine)
        verifier_instance = verifier.instance_id
        lines.append(worker_line(worker_note, worker.engine))
        lines.append(verifier_line(verifier_provider, verifier_instance, excluded))

        def _payload(step: MissionStep, attempt: int, carried: str) -> tuple[str, str]:
            """The step's declared artifact, with its producer made explicit.

            EVERY step's own contract declares the datum its work needs (see
            `step_capability`); the loop asks the fabric for it (through
            `jarvis.live_capability`) and records what really produced it, per
            attempt, so the report can print the truth instead of an assumed
            provenance.
            """
            datum = self._capabilities.resolve(
                step.id, mission_id=mission_id, goal=goal, attempt=attempt
            )
            return step_payload(
                step,
                mission_id=mission_id,
                goal=goal,
                step_ids=self._step_ids,
                attempt=attempt,
                carried=carried,
                goal_sha256=datum.datum if datum.field == "goal_sha256" else None,
                deliverable_sha256=datum.datum if datum.field == "sha256" else None,
                digest_source=datum.label,
            )

        orchestrator = StepOrchestrator(
            worker=worker,
            verifier=verifier,
            recovery=self.recovery,
            goal=goal,
            mission_id=mission_id,
            step_ids=self._step_ids,
            payload=_payload,
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
            lines.append(i5_refusal_line(verifier_provider))

        capability_datums = {
            (datum.step_id, datum.attempt): datum for datum in self._capabilities.datums
        }
        for record in records:
            lines.append(step_line(record))
            datum = capability_datums.get((record.step_id, record.attempt))
            if datum is not None and datum.label:
                lines.append(capability_line(datum))
        for act in acts:
            lines.append(recovery_action_line(act))

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
        lines.append(completion_line(decision.passed, event_type, state.state))

        # recover: the ladder decided, the ACT plane materialized
        if not accepted and acts:
            lines.append(recovery_halt_line(outcome, acts[-1]))
        elif acts:
            lines.append(recovery_materialized_line(acts))
        else:
            lines.append(recovery_none_line())

        # recall: write the outcome into memory, then read it back
        memory_note = (
            f"mission {mission_id} {completion} the goal {goal!r}; "
            f"{len(records)} step attempts, outcome {outcome}"
        )
        written = MemoryWriter(self.log).remember(
            content=memory_note, source=f"mission {mission_id}"
        )
        hits = Memory(log=self.log).recall(goal, limit=3)
        lines.append(recall_line(written.status, hits, goal))

        daemon = self._daemon_tick()
        lines.append(daemon_line(daemon))
        # Rebuilt from the log: `CoreService.projection()` is the boot-time
        # snapshot and would under-report after this run's appends.
        projection = MemoryProjection.rebuild(self.log)
        external_attempts = [r for r in records if r.external]
        return MissionReport(
            mission_id=mission_id,
            goal=goal,
            outcome=outcome,
            steps=tuple(records),
            artifacts=artifacts,
            lifecycle=state.state,
            completion=completion,
            recall_hits=len(hits),
            digest=projection.digest(),
            dispatch=dispatch_label(len(external_attempts)),
            daemon=daemon,
            worker=worker_label,
            verifier=verifier_summary(verifier_provider, verifier_instance, excluded),
            lines=tuple(lines),
            components=self.components(
                mission=True,
                worker_label=worker_label,
                verifier_label=verifier_component_label(verifier_provider, verifier_instance),
            ),
        )

    # -- the voice turn ----------------------------------------------------

    def voice_turn(
        self,
        utterance: str,
        *,
        audio: Path | str | None = None,
        answerer: Callable[[str], Any] | None = None,
    ) -> VoiceTurnReport:
        """One spoken turn - the turn itself is owned by `jarvis.live_voice`."""
        return self._voice.run(utterance, audio=audio, answerer=answerer)

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
        binaries = {
            name: bool(shutil.which(binary))
            for name, binary in (("bigpickle", "opencode"), ("antigravity", "agy"))
        }
        return components_lines(
            mission=mission,
            log_path=self.log_path(),
            projection_digest=projection.digest(),
            provider_count=len(self.service.provider_ids()),
            workspace=str(self.workspace),
            manifest_id=self._manifest_id,
            step_count=len(self._step_ids) or "n/a",
            capability_label=capability_component_label(
                self._capabilities.datums, self._capabilities.indexed_skills()
            ),
            worker_label=worker_label,
            verifier_label=verifier_label,
            binaries=binaries,
            daemon_status=daemon_status_label(len(self.leases)),
            stt_engine=self.stt_engine,
            tts_engine=self.tts_engine,
            gateway=gateway_label(
                configured=model_backend_configured(), answer_path=answer_path
            ),
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
