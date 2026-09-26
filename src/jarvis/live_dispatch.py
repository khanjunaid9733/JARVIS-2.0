from __future__ import annotations

"""The worker / verifier seam for the live loop.

Three separate objects, because "the worker must not adjudicate its own work"
is only true if they really are different things:

* `ExternalWorker` - produces the artifact in a REAL external process spawned
  through an existing L7 bridge: `validate_dispatch` preconditions fail closed,
  the child runs inside `ContainedProcess` containment (kill-on-close Job
  Object on Windows, process-group kill on POSIX, `taskkill /F /T` tree walk),
  the sandbox timeout terminates the whole tree, and the dispatch handle keeps
  the real PID. A worker's exit code is NOT a claim we accept: the artifact
  must exist inside the workspace jail or the attempt is a failure.
* `LocalWorker` - the labeled fallback. It writes the artifact in-process
  through the effect envelope and is reported as `local (NOT a dispatch)`.
  It is never described as external dispatch.
* `IndependentVerifier` - adjudicates. It runs the check in a FRESH process
  (own PID, own exit code, own containment) attributed to a provider that
  Invariant I5 excludes from the role the worker filled. It reads filesystem
  bytes only and never the worker's return value.
* `StepOrchestrator` - the runner's `StepVerifier` seam: runs the worker, then
  returns ONLY the verifier's datum. M3.2 exposes no worker hook, so a retry
  re-executes the worker here; the worker never sees the verification result.

Engine reality on this machine, evidenced and reported rather than hidden:
`opencode run` never responds non-interactively (killed at 200-240s, empty
output, no artifact) and `agy -p` completes but every tool call is blocked by
a malformed hook in the user's global plugin config, so neither can produce an
artifact here. The default worker is therefore the labeled local fallback;
`--worker external` performs the real dispatch and reports exactly what
happened.
"""

import json
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .kernel.effect_envelope import EffectFailure, EffectEnvelope
from .kernel.event_log import new_ulid
# Import directly from sub-modules to avoid triggering orchestrator/__init__.py
# which creates a circular import: bridges → orchestrator.__init__ → mission_runner
# → jarvis.supervisor → orchestrator → (deadlock on Python's import lock).
from .orchestrator.bridges.dispatch import validate_dispatch
from .orchestrator.bridges.process import TIMEOUT_EXIT_CODE, ContainedProcess
from .orchestrator.bridges.protocol import BridgeError, Sandbox, WorkerStatus
from .orchestrator.router import canonical_provider
from .supervisor import (
    Evidence,
    EvidenceLedger,
    EvidenceSource,
    LifecycleState,
    VerificationResult,
)

#: Which binary each provider identity actually spawns (one place, so a
#: provider can never be reported as an engine it does not run).
BRIDGE_BINARIES: Mapping[str, str] = {
    "bigpickle": "opencode",
    "opencode": "opencode",
    "freebuff": "opencode",
    "deepseek": "opencode",
    "antigravity": "agy",
    "agy": "agy",
}

COLLECT_GRACE_SECONDS = 5.0
POLL_SECONDS = 0.1


# ---------------------------------------------------------------------------
# datums
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkDatum:
    """What the worker produced for one attempt - a datum, never a claim."""

    engine: str
    external: bool
    artifact: str | None
    error: str | None = None
    handle_id: str | None = None
    process_id: int | None = None
    exit_code: int | None = None
    containment: str = ""
    output: str = ""


@dataclass(frozen=True)
class VerifyDatum:
    """The independent verdict: which provider, which process, what exit code."""

    ok: bool
    summary: str
    provider: str
    instance_id: str
    process_id: int | None = None
    exit_code: int | None = None
    digest: str = ""


@dataclass(frozen=True)
class StepRecord:
    """One step attempt: the worker datum and the independent verdict."""

    step_id: str
    attempt: int
    wrote: str | None
    worker_error: str | None
    verified: bool
    verification: str
    ladder: str = ""
    retry_carried: bool = False
    worker_engine: str = ""
    external: bool = False
    handle_id: str | None = None
    worker_pid: int | None = None
    worker_exit: int | None = None
    containment: str = ""
    verifier: str = ""
    verifier_instance: str = ""
    verifier_pid: int | None = None
    verifier_exit: int | None = None


# ---------------------------------------------------------------------------
# the declared artifact contract (shared by worker, payload and verifier)
# ---------------------------------------------------------------------------

PLAN_STEP = "plan"
DELIVER_STEP = "deliver"
ATTEST_STEP = "attest"


def goal_digest(goal: str) -> str:
    import hashlib

    return hashlib.sha256(goal.encode("utf-8")).hexdigest()


def step_payload(
    step: MissionStepLike,  # noqa: F821 - see alias below
    *,
    mission_id: str,
    goal: str,
    step_ids: Sequence[str],
    attempt: int,
    carried: str,
    deliverable_digest: str,
    base_dir: str = "artifacts",
    order_dir: str = "work_orders",
) -> tuple[str, str]:
    """The step's declared artifact path and exact bytes."""
    if step.id == PLAN_STEP:
        relative = f"{order_dir}/{mission_id}.json"
        body: dict[str, Any] = {
            "mission_id": mission_id,
            "goal": goal,
            "goal_sha256": goal_digest(goal),
            "attempt": attempt,
            "steps": list(step_ids),
        }
    elif step.id == ATTEST_STEP:
        deliverable = f"{base_dir}/{mission_id}.json"
        relative = f"{deliverable}.sha256"
        body = {
            "deliverable": deliverable,
            "sha256": deliverable_digest,
            "mission_id": mission_id,
            "attempt": attempt,
        }
    else:
        relative = f"{base_dir}/{mission_id}.json"
        body = {
            "mission_id": mission_id,
            "step": step.id,
            "goal": goal,
            "goal_sha256": goal_digest(goal),
            "attempt": attempt,
            "recovered": attempt > 1,
            "recovery_context": carried,
        }
    return relative, json.dumps(body, sort_keys=True, indent=2) + "\n"


def step_expectations(
    step_id: str,
    *,
    mission_id: str,
    goal: str,
    step_ids: Sequence[str],
    deliverable: str,
    base_dir: str = "artifacts",
    order_dir: str = "work_orders",
) -> dict[str, Any]:
    """What the independent verifier must find for this step, as pure data."""
    if step_id == PLAN_STEP:
        return {
            "kind": PLAN_STEP,
            "mission_id": mission_id,
            "goal": goal,
            "steps": len(step_ids),
            "path": f"{order_dir}/{mission_id}.json",
        }
    if step_id == ATTEST_STEP:
        return {
            "kind": ATTEST_STEP,
            "mission_id": mission_id,
            "deliverable": deliverable,
            "path": f"{deliverable}.sha256",
        }
    return {
        "kind": DELIVER_STEP,
        "mission_id": mission_id,
        "goal_sha256": goal_digest(goal),
        "path": f"{base_dir}/{mission_id}.json",
    }


#: The independent check, run as a FRESH process by `IndependentVerifier`.
#: It receives (workspace, relative_path, expectations_json) and exits 0 only
#: when the artifact really satisfies the declared contract.
VERIFIER_PROGRAM = r'''
import hashlib, json, pathlib, sys

root = pathlib.Path(sys.argv[1]).resolve()
rel = sys.argv[2]
exp = json.loads(sys.argv[3])

target = (root / rel).resolve()
if target != root and root not in target.parents:
    print("REFUSED: artifact path escapes the workspace jail")
    sys.exit(2)
if not target.is_file():
    print("MISSING: no artifact at %s" % rel)
    sys.exit(3)

data = target.read_bytes()
try:
    body = json.loads(data.decode("utf-8"))
except Exception as exc:
    print("UNPARSEABLE: %s" % type(exc).__name__)
    sys.exit(4)

if exp.get("mission_id") and body.get("mission_id") != exp["mission_id"]:
    print("MISMATCH: artifact belongs to another mission")
    sys.exit(5)

kind = exp["kind"]
if kind == "plan":
    if body.get("goal") != exp["goal"] or len(body.get("steps") or []) != exp["steps"]:
        print("MISMATCH: work order goal/steps")
        sys.exit(6)
elif kind == "deliver":
    if body.get("goal_sha256") != exp["goal_sha256"]:
        print("MISMATCH: deliverable goal digest")
        sys.exit(7)
elif kind == "attest":
    dep = (root / str(body.get("deliverable", ""))).resolve()
    if dep == root or root not in dep.parents or not dep.is_file():
        print("MISMATCH: attested deliverable missing")
        sys.exit(8)
    if body.get("sha256") != hashlib.sha256(dep.read_bytes()).hexdigest():
        print("MISMATCH: attestation does not match the deliverable on disk")
        sys.exit(9)

print(json.dumps({
    "verdict": "VERIFIED",
    "sha256": hashlib.sha256(data).hexdigest(),
    "bytes": len(data),
}, sort_keys=True))
'''

_VERIFIER_REFUSALS = {
    2: "refused: artifact path escapes the workspace jail",
    3: "missing: the worker produced no artifact",
    4: "unparseable artifact",
    5: "artifact belongs to another mission",
    6: "work order does not match the goal",
    7: "deliverable does not match the goal",
    8: "attested deliverable missing",
    9: "attestation does not match the deliverable on disk",
}


# `step_payload`/`step_expectations` take a `MissionStep`-shaped object; kept as
# a string annotation above to avoid importing the orchestrator at module load.
MissionStepLike = Any


# ---------------------------------------------------------------------------
# workers
# ---------------------------------------------------------------------------


class LocalWorker:
    """The labeled fallback: writes the artifact in-process.

    Never reported as a dispatch, and never given the verifier's verdict.
    """

    def __init__(
        self,
        write_artifact: Callable[..., str | None],
        faults: Mapping[str, int] | None = None,
        on_phase: Callable[[str, str, str], None] | None = None,
    ) -> None:
        self._write = write_artifact
        self._faults = dict(faults or {})
        self._on_phase = on_phase or (lambda step_id, phase, worker: None)

    @property
    def engine(self) -> str:
        return "local (in-process, NOT a dispatch)"

    def run(
        self,
        step: Any,
        *,
        mission_id: str,
        relative: str,
        content: str,
        attempt: int,
        carried: str,
    ) -> WorkDatum:
        self._on_phase(step.id, "INTENT", "local")
        self._on_phase(step.id, "STARTED", "local")
        budget = self._faults.get(step.id, 0)
        if attempt <= budget:
            self._on_phase(step.id, "COMPLETED", "declared-fault")
            return WorkDatum(
                engine=self.engine,
                external=False,
                artifact=None,
                error=f"declared transient fault (attempt {attempt} of {budget})",
                containment="declared-fault",
            )
        error = self._write(
            mission_id=mission_id,
            step_id=step.id,
            attempt=attempt,
            relative=relative,
            content=content,
        )
        self._on_phase(step.id, "COMPLETED", "local")
        if error is not None:
            return WorkDatum(
                engine=self.engine,
                external=False,
                artifact=None,
                error=error,
                containment="effect-refused",
            )
        return WorkDatum(engine=self.engine, external=False, artifact=relative)


class ExternalWorker:
    """A real external process, spawned through an existing L7 bridge."""

    def __init__(
        self,
        *,
        provider: str,
        binary: str,
        bridge: Any,
        workspace: Path,
        timeout: float,
        resolve_jailed: Callable[[str], Path],
        on_phase: Callable[[str, str, str], None] | None = None,
    ) -> None:
        self._provider = provider
        self._binary = binary
        self._bridge = bridge
        self._workspace = workspace
        self._timeout = timeout
        self._resolve_jailed = resolve_jailed
        self._on_phase = on_phase or (lambda step_id, phase, worker: None)

    @property
    def engine(self) -> str:
        return f"external {self._binary!r} via the {self._provider} bridge"

    def prompt(self, step: Any, relative: str, content: str, carried: str) -> str:
        tail = f"\n{carried}\n" if carried else ""
        return (
            f"Write the file {relative} relative to your current working directory "
            f"with EXACTLY the following content and nothing else:{tail}\n"
            f"{content}\n"
            "Then reply DONE. Do not modify any other file.\n"
        )

    def run(
        self,
        step: Any,
        *,
        mission_id: str,
        relative: str,
        content: str,
        attempt: int,
        carried: str,
    ) -> WorkDatum:
        del mission_id  # the artifact itself carries the mission identity
        prompt = self.prompt(step, relative, content, carried)
        self._on_phase(step.id, "INTENT", self._binary)
        try:
            validate_dispatch(
                prompt,
                self._workspace,
                Sandbox(allowed_paths=(self._workspace,), timeout_seconds=self._timeout),
            )
        except BridgeError as exc:
            return WorkDatum(
                engine=self.engine,
                external=True,
                artifact=None,
                error=f"dispatch precondition refused: {type(exc).__name__}: {exc}",
                containment="precondition",
            )
        sandbox = Sandbox(allowed_paths=(self._workspace,), timeout_seconds=self._timeout)
        try:
            handle = self._bridge.submit(prompt, self._workspace, sandbox)
        except Exception as exc:  # a spawn fault is a datum, never a crash
            # STARTED is NOT recorded: the worker never started, so the
            # dispatch trace stays UNKNOWN rather than claiming an orphan.
            return WorkDatum(
                engine=self.engine,
                external=True,
                artifact=None,
                error=f"spawn failed ({self._binary!r}): {type(exc).__name__}: {exc}",
                containment="spawn-fault",
            )
        self._on_phase(step.id, "STARTED", self._binary)

        deadline = time.monotonic() + self._timeout + COLLECT_GRACE_SECONDS
        status = WorkerStatus.PENDING
        while time.monotonic() < deadline:
            status = self._bridge.status(handle)
            if status not in (WorkerStatus.PENDING, WorkerStatus.RUNNING):
                break
            time.sleep(POLL_SECONDS)

        if status in (WorkerStatus.PENDING, WorkerStatus.RUNNING):
            # Containment: terminate the worker AND its descendants.
            self._bridge.cancel(handle)
            self._on_phase(step.id, "COMPLETED", self._binary)
            return WorkDatum(
                engine=self.engine,
                external=True,
                artifact=None,
                error=(
                    f"worker exceeded the {self._timeout:g}s sandbox timeout; "
                    "the process tree was terminated"
                ),
                handle_id=handle.handle_id,
                process_id=handle.process_id,
                containment="timeout",
            )

        artifacts = self._bridge.collect(handle)
        self._on_phase(step.id, "COMPLETED", self._binary)
        if artifacts.exit_code == TIMEOUT_EXIT_CODE:
            # Containment already killed the tree; the datum says so explicitly.
            return WorkDatum(
                engine=self.engine,
                external=True,
                artifact=None,
                error=(
                    f"worker exceeded the {self._timeout:g}s sandbox timeout; the "
                    "process tree was terminated"
                ),
                handle_id=handle.handle_id,
                process_id=handle.process_id,
                exit_code=artifacts.exit_code,
                containment="timeout",
            )
        if artifacts.exit_code != 0:
            detail = (artifacts.stderr or artifacts.stdout or "").strip()[-240:]
            return WorkDatum(
                engine=self.engine,
                external=True,
                artifact=None,
                error=f"worker exited {artifacts.exit_code}: {detail or 'no output'}",
                handle_id=handle.handle_id,
                process_id=handle.process_id,
                exit_code=artifacts.exit_code,
                containment="failed",
            )

        # Exit 0 is not evidence: the artifact must EXIST inside the jail.
        try:
            target = self._resolve_jailed(relative)
            present = target.is_file()
        except Exception:
            present = False
        if not present:
            return WorkDatum(
                engine=self.engine,
                external=True,
                artifact=None,
                error=(
                    f"worker reported success (exit 0) but produced no artifact at "
                    f"{relative} inside the workspace jail"
                ),
                handle_id=handle.handle_id,
                process_id=handle.process_id,
                exit_code=0,
                containment="self-attested",
                output=(artifacts.stdout or "").strip()[-240:],
            )
        return WorkDatum(
            engine=self.engine,
            external=True,
            artifact=relative,
            handle_id=handle.handle_id,
            process_id=handle.process_id,
            exit_code=0,
            output=(artifacts.stdout or "").strip()[-240:],
        )


def select_worker(
    *,
    mode: str,
    provider: str,
    bridge: Any,
    binary: str | None,
    binary_present: bool,
    local: LocalWorker,
    external_factory: Callable[[], ExternalWorker],
) -> tuple[LocalWorker | ExternalWorker, str]:
    """Choose the worker and say why, in words the output can print verbatim."""
    if mode == "local":
        return local, "external dispatch not requested (--worker local); worker is local"
    if not binary_present or bridge is None or binary is None:
        if mode == "external":
            return local, (
                f"external REQUIRED but no engine for provider {provider!r} "
                f"(binary {binary or 'unknown'!r} not on PATH); falling back to local"
            )
        return local, (
            f"auto: no engine for provider {provider!r} "
            f"(binary {binary or 'unknown'!r} not on PATH); worker is local"
        )
    return external_factory(), f"worker is external ({binary} via the {provider} bridge)"


# ---------------------------------------------------------------------------
# the independent verifier
# ---------------------------------------------------------------------------


class IndependentVerifier:
    """Adjudicates in a fresh process; never reads the worker's return value."""

    def __init__(
        self,
        *,
        workspace: Path,
        provider: str,
        excluded: frozenset[str],
        timeout: float = 120.0,
    ) -> None:
        self.provider = provider
        self.instance_id = f"verifier-{new_ulid()}"
        self._workspace = workspace
        self._excluded = excluded
        self._timeout = timeout

    def verify(self, *, relative: str, expectations: dict[str, Any]) -> VerifyDatum:
        if canonical_provider(self.provider) in self._excluded:
            return VerifyDatum(
                ok=False,
                summary=(
                    f"INVARIANT I5: provider {self.provider!r} is excluded from "
                    "verification for this package (it filled the red-team role)"
                ),
                provider=self.provider,
                instance_id=self.instance_id,
            )
        command = [
            sys.executable,
            "-c",
            VERIFIER_PROGRAM,
            str(self._workspace),
            relative,
            json.dumps(expectations, sort_keys=True),
        ]
        process = ContainedProcess(command, self._workspace).start()
        try:
            code, out, err = process.wait(self._timeout)
        finally:
            process.close()
        digest = ""
        if code == 0:
            try:
                digest = json.loads(out.strip().splitlines()[-1])["sha256"]
            except Exception:
                digest = ""
        summary = (
            f"verified by a fresh process: {out.strip()}"
            if code == 0
            else _VERIFIER_REFUSALS.get(code, f"verifier exited {code}: {(err or out).strip()[-200:]}")
        )
        return VerifyDatum(
            ok=code == 0,
            summary=summary,
            provider=self.provider,
            instance_id=self.instance_id,
            process_id=process.pid,
            exit_code=code,
            digest=digest,
        )


# ---------------------------------------------------------------------------
# the runner's seam: worker then verifier, one datum out
# ---------------------------------------------------------------------------


class StepOrchestrator:
    """Implements M3.2's `StepVerifier` for the live loop.

    `verify()` runs the WORKER (a separate object) and returns ONLY the
    INDEPENDENT verifier's datum. The worker never supplies the value the
    ratchet reads, and never learns the verdict. The attempt counter lives
    here because `MissionRunner` has no worker hook: each retry re-executes
    the worker with the failure bytes the recovery engine materialized.
    """

    def __init__(
        self,
        *,
        worker: LocalWorker | ExternalWorker,
        verifier: IndependentVerifier,
        recovery: Any,
        goal: str,
        mission_id: str,
        step_ids: Sequence[str],
        payload: Callable[[Any, int, str], tuple[str, str]],
        expectations: Callable[[Any], dict[str, Any]],
        now: Callable[[], str],
        on_verify: Callable[[VerifyDatum], None] | None = None,
    ) -> None:
        self.worker = worker
        self.verifier = verifier
        self._recovery = recovery
        self._goal = goal
        self._mission_id = mission_id
        self._step_ids = tuple(step_ids)
        self._payload = payload
        self._expectations = expectations
        self._now = now
        self._on_verify = on_verify
        self._attempts: dict[str, int] = {}
        self._contexts: dict[str, str] = {}
        self.records: list[StepRecord] = []
        self.acts: list[Any] = []

    def verify(self, step: Any) -> VerificationResult:
        attempt = self._attempts.get(step.id, 0) + 1
        self._attempts[step.id] = attempt
        carried = self._contexts.get(step.id, "")

        relative, content = self._payload(step, attempt, carried)
        work = self.worker.run(
            step,
            mission_id=self._mission_id,
            relative=relative,
            content=content,
            attempt=attempt,
            carried=carried,
        )
        if work.artifact is None:
            verdict = VerifyDatum(
                ok=False,
                summary=work.error or "the worker produced nothing to verify",
                provider=self.verifier.provider,
                instance_id=self.verifier.instance_id,
                exit_code=None,
            )
        else:
            verdict = self.verifier.verify(
                relative=work.artifact, expectations=self._expectations(step)
            )
        if self._on_verify is not None:
            self._on_verify(verdict)

        observed_at = self._now()
        record = StepRecord(
            step_id=step.id,
            attempt=attempt,
            wrote=work.artifact,
            worker_error=work.error,
            verified=verdict.ok,
            verification=verdict.summary,
            retry_carried=bool(carried),
            worker_engine=work.engine,
            external=work.external,
            handle_id=work.handle_id,
            worker_pid=work.process_id,
            worker_exit=work.exit_code,
            containment=work.containment,
            verifier=verdict.provider,
            verifier_instance=verdict.instance_id,
            verifier_pid=verdict.process_id,
            verifier_exit=verdict.exit_code,
        )

        if not verdict.ok:
            # The ladder DECIDES; the recovery engine MATERIALIZES the action.
            # Same policy, same attempts, same fresh evidence as the runner's
            # own fold, so both reach the same rung.
            #
            # Rung choice, deliberately FILESYSTEM and not FRESH_VERIFIER: the
            # verdict IS a datum over filesystem bytes (a hash + an existence
            # check made by a fresh process). `supervisor.recovery._has_recovery_evidence`
            # tests `precedence >= EvidencePrecedence.FILESYSTEM` (7), so a
            # verifier declaring the FRESH_VERIFIER rung (6) is treated as
            # "no fresh recovery-relevant evidence" and forces RESTART where
            # the evidence plainly warrants RETRY. Reported as a finding; the
            # frozen supervisor semantics are untouched.
            ledger = EvidenceLedger(
                observed_at=observed_at,
                entries=(
                    Evidence.declare(
                        EvidenceSource.FILESYSTEM, verdict.summary, observed_at
                    ),
                ),
            )
            outcome = self._recovery.act(
                step=step,
                state=LifecycleState.FAILED,
                ledger=ledger,
                attempts_used=attempt,
                failure_snippet=verdict.summary,
                rollback_target=None,
            )
            self.acts.append(outcome)
            if outcome.retry is not None:
                self._contexts[step.id] = outcome.retry.prompt_suffix
            record = replace(record, ladder=outcome.action.value)

        self.records.append(record)
        return VerificationResult.decided(
            verdict.ok, EvidenceSource.FILESYSTEM, observed_at, verdict.summary
        )


__all__ = [
    "ATTEST_STEP",
    "BRIDGE_BINARIES",
    "COLLECT_GRACE_SECONDS",
    "DELIVER_STEP",
    "ExternalWorker",
    "IndependentVerifier",
    "LocalWorker",
    "PLAN_STEP",
    "StepOrchestrator",
    "StepRecord",
    "VERIFIER_PROGRAM",
    "VerifyDatum",
    "WorkDatum",
    "goal_digest",
    "select_worker",
    "step_expectations",
    "step_payload",
]
