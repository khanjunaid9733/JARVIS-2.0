from __future__ import annotations

"""Unit tests for L7 Bridges (tests/orchestrator/test_bridges.py).

The dispatch contract is ASYNCHRONOUS: ``submit`` spawns and returns a LIVE
handle, ``status`` polls, ``cancel`` terminates the process tree, and
``collect`` waits for termination before returning artifacts. Preconditions
(sandbox confinement, prompt length) are fail-closed and raise BEFORE a worker
is spawned.
"""

import os
import sys
import time
from pathlib import Path

import pytest

from jarvis.orchestrator.bridges import (
    ARGV_LIMIT_POSIX,
    ARGV_LIMIT_WINDOWS,
    AgyBridge,
    Artifacts,
    DeepSeekBridge,
    DefaultSubprocessRunner,
    Handle,
    OpenCodeBridge,
    PromptTooLong,
    Sandbox,
    SandboxViolation,
    WorkerDispatch,
    WorkerStatus,
    argv_limit,
    validate_dispatch,
)


class MockCommandRunner:
    """Deterministic in-memory command runner for hermetic test execution."""

    def __init__(
        self,
        exit_code: int = 0,
        stdout: str = "mock output",
        stderr: str = "",
    ) -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.recorded_commands: list[tuple[list[str], Path, float | None]] = []

    def run(
        self, cmd: list[str], cwd: Path, timeout: float | None = None
    ) -> tuple[int, str, str]:
        self.recorded_commands.append((cmd, cwd, timeout))
        return self.exit_code, self.stdout, self.stderr


class BlockingRunner:
    """A runner that never returns until released - proves the dispatch is async."""

    def __init__(self) -> None:
        import threading

        self.gate = threading.Event()

    def run(self, cmd: list[str], cwd: Path, timeout: float | None = None):
        self.gate.wait(10)
        return 0, "", ""


class _ProbeBridge(WorkerDispatch):
    """A dispatch whose worker is a real, hermetic Python process."""

    handle_prefix = "probe"

    def __init__(self, script: str) -> None:
        super().__init__()
        self._script = script

    def _argv(self, prompt: str, workdir: Path) -> list[str]:
        return [sys.executable, "-c", self._script, prompt]


# ---------------------------------------------------------------------------
# Provider argument vectors
# ---------------------------------------------------------------------------


def test_opencode_bridge_submit_and_collect(tmp_path: Path) -> None:
    runner = MockCommandRunner(exit_code=0, stdout="opencode finished")
    bridge = OpenCodeBridge(runner=runner)
    sandbox = Sandbox(timeout_seconds=60.0)

    handle = bridge.submit("implement feature X", tmp_path, sandbox)
    assert isinstance(handle, Handle)
    assert handle.workdir == tmp_path

    artifacts = bridge.collect(handle)  # collect waits for termination
    assert isinstance(artifacts, Artifacts)
    assert artifacts.exit_code == 0
    assert artifacts.stdout == "opencode finished"
    assert bridge.status(handle) is WorkerStatus.COMPLETED
    assert runner.recorded_commands == [
        (["opencode", "run", "implement feature X"], tmp_path, 60.0)
    ]


def test_opencode_bridge_auto_approve_and_model(tmp_path: Path) -> None:
    runner = MockCommandRunner(exit_code=0, stdout="done")
    bridge = OpenCodeBridge(
        runner=runner,
        provider_model="google/gemini-3.1-flash-lite",
        auto_approve=True,
    )
    handle = bridge.submit("auto task", tmp_path, Sandbox(timeout_seconds=45.0))
    bridge.collect(handle)

    assert runner.recorded_commands == [
        (
            ["opencode", "run", "--auto", "-m", "google/gemini-3.1-flash-lite", "auto task"],
            tmp_path,
            45.0,
        )
    ]


def test_opencode_bridge_failure(tmp_path: Path) -> None:
    runner = MockCommandRunner(exit_code=1, stderr="syntax error")
    bridge = OpenCodeBridge(runner=runner)

    handle = bridge.submit("broken code", tmp_path, Sandbox())
    artifacts = bridge.collect(handle)

    assert bridge.status(handle) is WorkerStatus.FAILED
    assert artifacts.exit_code == 1
    assert "syntax error" in artifacts.stderr


def test_agy_bridge_command_line(tmp_path: Path) -> None:
    runner = MockCommandRunner(exit_code=0, stdout="agy done")
    bridge = AgyBridge(runner=runner)

    handle = bridge.submit("verify architecture", tmp_path, Sandbox(timeout_seconds=120.0))
    bridge.collect(handle)

    assert bridge.status(handle) is WorkerStatus.COMPLETED
    assert runner.recorded_commands == [
        (
            [
                "agy",
                "-p",
                "verify architecture",
                "--dangerously-skip-permissions",
                "--add-dir",
                str(tmp_path),
            ],
            tmp_path,
            120.0,
        )
    ]


def test_deepseek_bridge_command_line(tmp_path: Path) -> None:
    runner = MockCommandRunner(exit_code=0, stdout="redteam report")
    bridge = DeepSeekBridge(runner=runner, provider_model="deepseek-r1")

    handle = bridge.submit("redteam review", tmp_path, Sandbox(timeout_seconds=90.0))
    bridge.collect(handle)

    assert bridge.status(handle) is WorkerStatus.COMPLETED
    assert runner.recorded_commands == [
        (["opencode", "run", "--model=deepseek-r1", "redteam review"], tmp_path, 90.0)
    ]


def test_unknown_handle_returns_failed_and_error_artifacts(tmp_path: Path) -> None:
    # Still open (F-M3.3-FB-8): an unknown handle is reported as FAILED with a
    # fabricated exit code rather than as an unknown dispatch.
    bridge = OpenCodeBridge()
    fake_handle = Handle(handle_id="non-existent", workdir=tmp_path)
    assert bridge.status(fake_handle) is WorkerStatus.FAILED
    artifacts = bridge.collect(fake_handle)
    assert artifacts.exit_code == 1
    assert "Unknown handle" in artifacts.stderr


# ---------------------------------------------------------------------------
# Asynchronous lifecycle (F-M3.3-FB-3)
# ---------------------------------------------------------------------------


def test_submit_returns_a_live_handle_while_the_worker_runs(tmp_path: Path) -> None:
    runner = BlockingRunner()
    bridge = OpenCodeBridge(runner=runner)

    started = time.monotonic()
    handle = bridge.submit("p", tmp_path, Sandbox())
    elapsed = time.monotonic() - started

    assert elapsed < 5.0, "submit blocked on the worker instead of dispatching"
    assert bridge.status(handle) is WorkerStatus.RUNNING

    runner.gate.set()
    bridge.collect(handle)
    assert bridge.status(handle) is WorkerStatus.COMPLETED


def test_cancel_settles_a_dispatch_cancelled(tmp_path: Path) -> None:
    runner = BlockingRunner()
    bridge = OpenCodeBridge(runner=runner)
    handle = bridge.submit("p", tmp_path, Sandbox())

    assert bridge.status(handle) is WorkerStatus.RUNNING
    bridge.cancel(handle)
    assert bridge.status(handle) is WorkerStatus.CANCELLED

    runner.gate.set()
    bridge.collect(handle)
    assert bridge.status(handle) is WorkerStatus.CANCELLED


def test_cancel_is_not_clobbered_by_a_later_successful_completion(
    tmp_path: Path,
) -> None:
    """A cancelled dispatch stays CANCELLED even if the worker would have
    exited 0: once terminal, CANCELLED is final."""
    runner = BlockingRunner()
    bridge = OpenCodeBridge(runner=runner)
    handle = bridge.submit("p", tmp_path, Sandbox())

    assert bridge.status(handle) is WorkerStatus.RUNNING
    bridge.cancel(handle)
    runner.gate.set()  # the worker now returns exit code 0
    bridge.collect(handle)

    assert bridge.status(handle) is WorkerStatus.CANCELLED


def test_cancel_is_idempotent_and_ignores_unknown_handles(tmp_path: Path) -> None:
    bridge = OpenCodeBridge(runner=MockCommandRunner(exit_code=0))
    handle = bridge.submit("p", tmp_path, Sandbox())
    bridge.collect(handle)
    bridge.cancel(handle)  # already terminal
    bridge.cancel(Handle(handle_id="nope", workdir=tmp_path))  # unknown
    assert bridge.status(handle) is WorkerStatus.COMPLETED


def test_a_real_process_dispatch_exposes_a_pid_and_collects_stdout(
    tmp_path: Path,
) -> None:
    bridge = _ProbeBridge("import sys, time; time.sleep(0.4); print('ran:' + sys.argv[1])")
    handle = bridge.submit("hello", tmp_path, Sandbox(timeout_seconds=30))

    assert handle.process_id is not None, "the dispatch does not own a real process"
    assert bridge.status(handle) is WorkerStatus.RUNNING

    artifacts = bridge.collect(handle)
    assert artifacts.exit_code == 0
    assert artifacts.stdout.strip() == "ran:hello"
    assert bridge.status(handle) is WorkerStatus.COMPLETED


def test_cancel_terminates_a_real_process(tmp_path: Path) -> None:
    bridge = _ProbeBridge("import time; time.sleep(30)")
    handle = bridge.submit("x", tmp_path, Sandbox(timeout_seconds=60))

    assert bridge.status(handle) is WorkerStatus.RUNNING
    bridge.cancel(handle)
    bridge.collect(handle)

    assert bridge.status(handle) is WorkerStatus.CANCELLED


# ---------------------------------------------------------------------------
# Sandbox confinement (F-M3.3-FB-1)
# ---------------------------------------------------------------------------


def test_validate_dispatch_returns_the_callers_path_unchanged(tmp_path: Path) -> None:
    assert validate_dispatch("p", tmp_path, Sandbox()) == tmp_path


def test_submit_refuses_a_workdir_outside_the_sandbox(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    runner = MockCommandRunner()

    with pytest.raises(SandboxViolation):
        OpenCodeBridge(runner=runner).submit("p", outside, Sandbox(allowed_paths=(allowed,)))

    assert runner.recorded_commands == []


def test_submit_accepts_a_workdir_nested_inside_the_sandbox(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    nested = allowed / "pkg"
    nested.mkdir(parents=True)
    runner = MockCommandRunner()

    bridge = OpenCodeBridge(runner=runner)
    handle = bridge.submit("p", nested, Sandbox(allowed_paths=(allowed,)))
    bridge.collect(handle)

    assert runner.recorded_commands[0][1] == nested


# ---------------------------------------------------------------------------
# Prompt bounds (F-M3.3-FB-6)
# ---------------------------------------------------------------------------


def test_argv_limit_is_platform_specific() -> None:
    assert argv_limit("win32") == ARGV_LIMIT_WINDOWS
    assert argv_limit("linux") == ARGV_LIMIT_POSIX
    assert argv_limit("darwin") == ARGV_LIMIT_POSIX


def test_submit_refuses_an_over_limit_prompt(tmp_path: Path) -> None:
    runner = MockCommandRunner()
    huge = "x" * (argv_limit() + 1)

    with pytest.raises(PromptTooLong):
        OpenCodeBridge(runner=runner).submit(huge, tmp_path, Sandbox())

    assert runner.recorded_commands == []


def test_submit_accepts_a_prompt_at_the_limit(tmp_path: Path) -> None:
    runner = MockCommandRunner()
    at_limit = "x" * argv_limit()

    bridge = OpenCodeBridge(runner=runner)
    handle = bridge.submit(at_limit, tmp_path, Sandbox())
    bridge.collect(handle)

    assert runner.recorded_commands[0][0][2] == at_limit


# ---------------------------------------------------------------------------
# Process containment (F-M3.3-FB-2)
# ---------------------------------------------------------------------------


def test_default_runner_reports_a_timeout_as_exit_code_124(tmp_path: Path) -> None:
    rc, out, err = DefaultSubprocessRunner().run(
        [sys.executable, "-c", "import time; time.sleep(30)"], cwd=tmp_path, timeout=1.0
    )
    assert rc == 124
    assert out == ""
    assert "TimeoutExpired" in err


def test_default_runner_kills_the_whole_tree_on_timeout(tmp_path: Path) -> None:
    """A killed worker must not leave a descendant holding worktree locks."""
    marker = tmp_path / "grandchild-survived.txt"
    grandchild = (
        "import pathlib, time; time.sleep(2); "
        f"pathlib.Path(r'{marker}').write_text('survived')"
    )
    parent = (
        "import subprocess, sys, time\n"
        f"subprocess.Popen([sys.executable, '-c', {grandchild!r}],\n"
        "                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,\n"
        "                 stderr=subprocess.DEVNULL)\n"
        "time.sleep(30)\n"
    )

    rc, _out, _err = DefaultSubprocessRunner().run(
        [sys.executable, "-c", parent], cwd=tmp_path, timeout=0.6
    )
    assert rc == 124

    time.sleep(3.0)  # longer than the grandchild's own sleep
    assert not marker.exists(), "a descendant survived the timeout kill"


def test_default_runner_reports_a_spawn_fault_instead_of_raising(tmp_path: Path) -> None:
    rc, out, err = DefaultSubprocessRunner().run(
        [sys.executable, "-c", "print('x')", "y" * (ARGV_LIMIT_WINDOWS + 8192)],
        cwd=tmp_path,
        timeout=30,
    )
    assert rc == 1
    assert out == ""
    assert err != ""


def _make_shim(directory: Path, name: str) -> Path:
    """Install ``name`` on disk the way npm does: as a script, not an image."""
    body = directory / f"{name}_body.py"
    body.write_text(
        'import pathlib\n'
        'pathlib.Path(__file__).with_name("marker.txt").write_text("ran")\n',
        encoding="utf-8",
    )
    if sys.platform == "win32":
        shim = directory / f"{name}.cmd"
        shim.write_text(f'@ECHO off\r\n"{sys.executable}" "{body}"\r\n', encoding="utf-8")
    else:
        shim = directory / name
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{body}"\n', encoding="utf-8")
        shim.chmod(0o755)
    return shim


def test_a_path_shim_is_launchable_through_the_dispatch_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A CLI installed only as a shim must SPAWN, not report a spawn fault.

    Regression (measured on this host): the bridge built argv from the bare
    name - ``["opencode", "run", prompt]`` - and Windows ``CreateProcess``
    appends only ``.exe`` to a bare name, so ``opencode.CMD`` (the real, npm-
    installed engine, with no ``opencode.exe`` beside it) raised
    ``FileNotFoundError [WinError 2]``. The engine looked absent when it was
    only unlaunchable, and a whole mission was refused as ``spawn-fault``.
    """
    tools = tmp_path / "tools"
    tools.mkdir()
    _make_shim(tools, "jvshimprobe")
    monkeypatch.setenv("PATH", str(tools) + os.pathsep + os.environ.get("PATH", ""))

    rc, out, err = DefaultSubprocessRunner().run(["jvshimprobe"], cwd=tmp_path, timeout=30)

    assert rc == 0, (out, err)
    assert (tools / "marker.txt").read_text(encoding="utf-8") == "ran"


def test_a_name_that_is_not_installed_still_reports_a_fault(tmp_path: Path) -> None:
    """Resolution must not turn an absent engine into a crash or a silence."""
    rc, out, err = DefaultSubprocessRunner().run(
        ["jv-definitely-not-installed-xyz"], cwd=tmp_path, timeout=30
    )
    assert rc == 1
    assert out == ""
    assert "FileNotFoundError" in err
