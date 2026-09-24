from __future__ import annotations

"""Hostile-condition tests for the worker / verifier seam.

The seam is exercised for real where it matters: a real external process is
spawned under the production dispatch lifecycle and containment, a real
timeout kills the process tree, and a FRESH process independently verifies the
artifact. Only the engine's argv is supplied by the test (the `CommandRunner`
seam the bridges already expose), because the engines installed on this
machine cannot run non-interactively - see `tests/test_live.py` and the
`--worker external` evidence in the report.

Nothing here reaches the network and no external agent binary is invoked.
"""

import json
import sys

import pytest

from jarvis.bootstrap import CoreService
from jarvis.kernel.memory_projection import MemoryProjection
from jarvis.live import LiveRuntime
from jarvis.live_dispatch import (
    ExternalWorker,
    IndependentVerifier,
    LocalWorker,
    select_worker,
)
from jarvis.orchestrator.bridges.dispatch import WorkerDispatch
from jarvis.orchestrator.router import Capability, ProviderProfile, Router

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


# ---------------------------------------------------------------------------
# a test-local bridge: production lifecycle + containment, test-supplied argv
# ---------------------------------------------------------------------------

#: A worker that honours the prompt: it reads the target path and the exact
#: content out of the prompt it was given (no test knowledge of the artifact).
WRITER_PROGRAM = r"""
import pathlib, re, sys

prompt = sys.argv[1]
target = re.search(r"Write the file (\S+) relative", prompt).group(1)
content = prompt.split("and nothing else:")[1].split("Then reply DONE")[0].strip("\n")
path = pathlib.Path(target)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(content, encoding="utf-8")
print("DONE")
"""

#: A worker that claims success without producing anything (exit 0, no file).
SILENT_PROGRAM = "print('DONE')"

#: A worker that writes OUTSIDE the workspace jail and claims success.
ESCAPE_PROGRAM = (
    "import pathlib; pathlib.Path('../escaped.json').write_text('{}'); print('DONE')"
)

#: A worker that never finishes inside the sandbox timeout.
SLEEP_PROGRAM = "import time; time.sleep(30)"


class _ProbeBridge(WorkerDispatch):
    """Production dispatch/containment, test-supplied argument vector."""

    handle_prefix = "probe"

    def __init__(self, program: str, runner: object | None = None) -> None:
        super().__init__(runner=runner)
        self._program = program

    def _argv(self, prompt: str, workdir):
        del workdir
        return [sys.executable, "-c", self._program, prompt]


class _FakeProcess:
    def __init__(self, exit_code: int, stdout: str, stderr: str) -> None:
        self.pid = 4242
        self._result = (exit_code, stdout, stderr)
        self.terminated = False
        self.closed = False

    def wait(self, timeout=None):
        return self._result

    def terminate(self):
        self.terminated = True

    def close(self):
        self.closed = True


class _ScriptedRunner:
    """A runner that produces a chosen outcome (or faults) without a process."""

    def __init__(
        self,
        *,
        exit_code: int = 0,
        stdout: str = "",
        stderr: str = "",
        raise_on_start: Exception | None = None,
    ) -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.raise_on_start = raise_on_start
        self.terminated = False
        self.processes: list[_FakeProcess] = []

    def start(self, cmd, cwd):
        if self.raise_on_start is not None:
            raise self.raise_on_start
        process = _FakeProcess(self.exit_code, self.stdout, self.stderr)
        self.processes.append(process)
        return process

    def terminate(self):
        self.terminated = True

    def run(self, cmd, cwd, timeout=None):
        return self.exit_code, self.stdout, self.stderr


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    for name in ("JARVIS_MODEL_API_KEY", "JARVIS_MODEL_BASE_URL", "JARVIS_STT_CMD"):
        monkeypatch.delenv(name, raising=False)
    service = CoreService(tmp_path).start()
    live = LiveRuntime(service)
    yield live
    service.close()


def _use_engine(live: LiveRuntime, program: str, *, runner=None, binary: str = "probe") -> None:
    """Point the implementer provider at a real external engine for this test."""
    live.bridges["bigpickle"] = _ProbeBridge(program, runner=runner)
    # keep the reported engine honest: it names the binary actually spawned
    live._engine_binary = binary  # noqa: SLF001 - test hook


def _external_mission(live: LiveRuntime, goal: str = "do the work externally", **kwargs):
    return live.run_goal(
        goal,
        worker_mode="external",
        worker_provider="bigpickle",
        worker_timeout=kwargs.pop("worker_timeout", 30.0),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# a real external process does the work; a different provider verifies it
# ---------------------------------------------------------------------------


def test_real_external_process_produces_the_artifact_and_another_provider_verifies(
    runtime, monkeypatch
):
    # the production code path resolves the binary through BRIDGE_BINARIES; the
    # test supplies a real, usable command in the same slot.
    monkeypatch.setitem(
        __import__("jarvis.live_dispatch", fromlist=["BRIDGE_BINARIES"]).BRIDGE_BINARIES,
        "bigpickle",
        sys.executable,
    )
    _use_engine(runtime, WRITER_PROGRAM)
    report = _external_mission(runtime)

    assert report.worker.startswith("worker is external")
    assert report.outcome == "ACCEPTED"
    assert report.completion == "completed"

    external = [record for record in report.steps if record.external]
    assert len(external) == 3, "every step ran through the external bridge"
    for record in external:
        assert record.verified is True
        assert record.worker_pid and record.worker_pid > 0      # a real child PID
        assert record.worker_exit == 0
        assert record.handle_id and record.handle_id.startswith("probe-")
        # the verdict came from a different process, attributed to another provider
        assert record.verifier_pid and record.verifier_pid != record.worker_pid
        assert record.verifier == "antigravity" not in (None, "")
        assert record.verifier_exit == 0

    # the artifact really exists, inside the jail
    deliverable = runtime.workspace / "artifacts" / f"{report.mission_id}.json"
    body = json.loads(deliverable.read_text(encoding="utf-8"))
    assert body["mission_id"] == report.mission_id
    assert deliverable.resolve().is_relative_to(runtime.workspace.resolve())

    # and the durable store agrees
    assert runtime.log.verify_chain() is True
    assert MemoryProjection.rebuild(runtime.log).event_count > 0


# ---------------------------------------------------------------------------
# hostile conditions
# ---------------------------------------------------------------------------


def test_missing_engine_falls_back_and_says_which_binary_is_missing():
    local = LocalWorker(lambda **kwargs: None)
    worker, note = select_worker(
        mode="external",
        provider="bigpickle",
        bridge=None,
        binary="opencode",
        binary_present=False,
        local=local,
        external_factory=lambda: pytest.fail("must not build an external worker"),
    )
    assert worker is local
    assert "REQUIRED" in note and "opencode" in note


def test_insufficient_privilege_is_a_spawn_fault_not_a_crash(runtime):
    _use_engine(
        runtime, WRITER_PROGRAM, runner=_ScriptedRunner(raise_on_start=PermissionError("denied"))
    )
    report = _external_mission(runtime)

    assert report.outcome != "ACCEPTED"
    assert report.completion == "refused"
    first = report.steps[0]
    assert first.external is True
    assert first.containment == "spawn-fault"
    assert "PermissionError" in (first.worker_error or "")


def test_a_failing_binary_refuses_completion(runtime):
    _use_engine(runtime, WRITER_PROGRAM, runner=_ScriptedRunner(exit_code=3, stderr="boom"))
    report = _external_mission(runtime, worker_timeout=10.0)

    assert report.completion == "refused"
    assert report.outcome == "HELD"
    assert report.artifacts == ()
    assert all(record.verified is False for record in report.steps)
    assert any("exited 3" in (record.worker_error or "") for record in report.steps)


def test_a_worker_exceeding_the_timeout_has_its_process_tree_terminated(runtime):
    _use_engine(runtime, SLEEP_PROGRAM)
    report = _external_mission(runtime, worker_timeout=1.0)

    timeouts = [record for record in report.steps if record.containment == "timeout"]
    assert timeouts, "the sandbox timeout must trigger containment"
    assert "process tree was terminated" in (timeouts[0].worker_error or "")
    assert report.artifacts == ()
    assert report.completion == "refused"


def test_a_worker_writing_outside_the_jail_is_not_accepted(runtime):
    _use_engine(runtime, ESCAPE_PROGRAM)
    report = _external_mission(runtime, worker_timeout=15.0)

    assert report.artifacts == ()
    assert report.completion == "refused"
    escaped = [record for record in report.steps if record.containment == "self-attested"]
    assert escaped, "an artifact outside the jail must not count as produced"
    assert all(record.verified is False for record in report.steps)
    # Documented limit, not a hidden one: the jail governs what we ACCEPT.
    # `Sandbox.allowed_paths` is a fail-closed precondition on the workdir, and
    # nothing here claims an external process cannot write elsewhere on disk
    # (`network_allowed`/`max_memory_mb` are declared-but-unenforced too).


def test_a_worker_claiming_success_without_an_artifact_never_completes(runtime):
    """The heart of the seam: exit 0 is not evidence."""
    _use_engine(runtime, SILENT_PROGRAM)
    report = _external_mission(runtime, worker_timeout=15.0)

    assert report.outcome != "ACCEPTED"
    assert report.completion == "refused"
    assert report.artifacts == ()
    assert all(record.verified is False for record in report.steps)
    assert any("produced no artifact" in (record.worker_error or "") for record in report.steps)
    # and the halt is recorded as a refusal, never a completion
    assert "task.completed" not in [event.event_type for event in runtime.log.replay()]
    assert "task.completion_refused" in [event.event_type for event in runtime.log.replay()]


def test_verifier_refuses_an_artifact_from_another_mission(runtime, tmp_path):
    verifier = IndependentVerifier(
        workspace=runtime.workspace,
        provider="antigravity",
        excluded=frozenset({"freebuff"}),
    )
    runtime.workspace.mkdir(parents=True, exist_ok=True)
    other = runtime.workspace / "artifacts"
    other.mkdir(parents=True, exist_ok=True)
    (other / "m.json").write_text(
        json.dumps({"mission_id": "some-other-mission", "goal_sha256": "x"}),
        encoding="utf-8",
    )
    verdict = verifier.verify(
        relative="artifacts/m.json",
        expectations={"kind": "deliver", "mission_id": "mine", "goal_sha256": "x"},
    )
    assert verdict.ok is False
    assert "another mission" in verdict.summary


def test_two_runs_do_not_share_a_verifier(runtime):
    first = _external_mission(runtime, "first goal")
    second = _external_mission(runtime, "second goal")

    first_ids = {record.verifier_instance for record in first.steps}
    second_ids = {record.verifier_instance for record in second.steps}
    assert first_ids and second_ids
    assert first_ids.isdisjoint(second_ids), "a verifier instance must not be reused across runs"
    assert first.mission_id != second.mission_id


def test_invariant_i5_is_enforced_not_asserted(runtime):
    """When the only verification provider is the red-team provider, refuse."""
    runtime.router = Router(
        {
            "freebuff": ProviderProfile(
                name="freebuff",
                capabilities=frozenset(
                    {Capability.REDTEAM_V1, Capability.VERIFICATION_V1, Capability.IMPLEMENTATION_V1}
                ),
            )
        }
    )
    report = runtime.run_goal("the same provider must not verify itself")

    assert report.outcome == "HELD"
    assert report.steps == ()
    assert report.completion == "refused"
    assert "I5" in "\n".join(report.lines)
    assert "VIOLATED" in "\n".join(report.lines)
    assert "task.completed" not in [event.event_type for event in runtime.log.replay()]
