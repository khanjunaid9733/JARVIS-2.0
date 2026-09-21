from __future__ import annotations

"""Unit tests for L7 Bridges (tests/orchestrator/test_bridges.py)."""

from pathlib import Path
import pytest

from jarvis.orchestrator.bridges import (
    AgyBridge,
    Artifacts,
    CommandRunner,
    DeepSeekBridge,
    Handle,
    OpenCodeBridge,
    Sandbox,
    WorkerStatus,
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


def test_opencode_bridge_submit_and_collect(tmp_path: Path) -> None:
    runner = MockCommandRunner(exit_code=0, stdout="opencode finished")
    bridge = OpenCodeBridge(runner=runner)
    sandbox = Sandbox(timeout_seconds=60.0)

    handle = bridge.submit("implement feature X", tmp_path, sandbox)
    assert isinstance(handle, Handle)
    assert handle.workdir == tmp_path
    assert bridge.status(handle) == WorkerStatus.COMPLETED

    artifacts = bridge.collect(handle)
    assert isinstance(artifacts, Artifacts)
    assert artifacts.exit_code == 0
    assert artifacts.stdout == "opencode finished"
    assert runner.recorded_commands == [(["opencode", "run", "implement feature X"], tmp_path, 60.0)]


def test_opencode_bridge_failure(tmp_path: Path) -> None:
    runner = MockCommandRunner(exit_code=1, stderr="syntax error")
    bridge = OpenCodeBridge(runner=runner)
    sandbox = Sandbox()

    handle = bridge.submit("broken code", tmp_path, sandbox)
    assert bridge.status(handle) == WorkerStatus.FAILED

    artifacts = bridge.collect(handle)
    assert artifacts.exit_code == 1
    assert "syntax error" in artifacts.stderr


def test_agy_bridge_command_line(tmp_path: Path) -> None:
    runner = MockCommandRunner(exit_code=0, stdout="agy done")
    bridge = AgyBridge(runner=runner)
    sandbox = Sandbox(timeout_seconds=120.0)

    handle = bridge.submit("verify architecture", tmp_path, sandbox)
    assert bridge.status(handle) == WorkerStatus.COMPLETED
    assert runner.recorded_commands == [(
        ["agy", "-p", "verify architecture", "--dangerously-skip-permissions", "--add-dir", str(tmp_path)],
        tmp_path,
        120.0,
    )]


def test_deepseek_bridge_command_line(tmp_path: Path) -> None:
    runner = MockCommandRunner(exit_code=0, stdout="redteam report")
    bridge = DeepSeekBridge(runner=runner, provider_model="deepseek-r1")
    sandbox = Sandbox(timeout_seconds=90.0)

    handle = bridge.submit("redteam review", tmp_path, sandbox)
    assert bridge.status(handle) == WorkerStatus.COMPLETED
    assert runner.recorded_commands == [(
        ["opencode", "run", "--model=deepseek-r1", "redteam review"],
        tmp_path,
        90.0,
    )]


def test_unknown_handle_returns_failed_and_error_artifacts(tmp_path: Path) -> None:
    bridge = OpenCodeBridge()
    fake_handle = Handle(handle_id="non-existent", workdir=tmp_path)
    assert bridge.status(fake_handle) == WorkerStatus.FAILED
    artifacts = bridge.collect(fake_handle)
    assert artifacts.exit_code == 1
    assert "Unknown handle" in artifacts.stderr
