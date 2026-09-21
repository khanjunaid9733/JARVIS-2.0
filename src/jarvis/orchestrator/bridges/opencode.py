from __future__ import annotations

"""OpenCode (Big Pickle) L7 Bridge (ORCHESTRATOR_ARCHITECTURE.md §12).

Executes tasks using the OpenCode CLI (`opencode run "<prompt>"`).
Provides hermetic command execution via an injectable CommandRunner.
"""

import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .protocol import Artifacts, Bridge, CommandRunner, Handle, Sandbox, WorkerStatus


@dataclass
class _JobState:
    status: WorkerStatus
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    cancelled: bool = False


class _DefaultSubprocessRunner:
    """Default runner executing commands via subprocess."""

    def run(
        self, cmd: list[str], cwd: Path, timeout: float | None = None
    ) -> tuple[int, str, str]:
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=False,
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as e:
            stdout = e.stdout or ""
            stderr = (e.stderr or "") + "\nTimeoutExpired"
            return 124, stdout, stderr
        except Exception as e:
            return 1, "", str(e)


class OpenCodeBridge(Bridge):
    """Bridge adapter for OpenCode / Big Pickle workers."""

    def __init__(self, runner: CommandRunner | None = None) -> None:
        self._runner = runner or _DefaultSubprocessRunner()
        self._jobs: dict[str, _JobState] = {}

    def submit(self, prompt: str, workdir: Path, sandbox: Sandbox) -> Handle:
        handle_id = f"opencode-{uuid.uuid4().hex[:12]}"
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        handle = Handle(handle_id=handle_id, workdir=workdir, started_at=now)

        cmd = ["opencode", "run", prompt]
        self._jobs[handle_id] = _JobState(status=WorkerStatus.RUNNING)

        # Synchronous execution through the runner seam
        rc, out, err = self._runner.run(
            cmd, cwd=workdir, timeout=sandbox.timeout_seconds
        )

        job = self._jobs[handle_id]
        job.exit_code = rc
        job.stdout = out
        job.stderr = err
        if job.cancelled:
            job.status = WorkerStatus.CANCELLED
        elif rc == 0:
            job.status = WorkerStatus.COMPLETED
        else:
            job.status = WorkerStatus.FAILED

        return handle

    def status(self, handle: Handle) -> WorkerStatus:
        job = self._jobs.get(handle.handle_id)
        if not job:
            return WorkerStatus.FAILED
        return job.status

    def cancel(self, handle: Handle) -> None:
        job = self._jobs.get(handle.handle_id)
        if job and job.status in (WorkerStatus.PENDING, WorkerStatus.RUNNING):
            job.cancelled = True
            job.status = WorkerStatus.CANCELLED

    def collect(self, handle: Handle) -> Artifacts:
        job = self._jobs.get(handle.handle_id)
        if not job:
            return Artifacts(exit_code=1, stdout="", stderr="Unknown handle")
        return Artifacts(
            exit_code=job.exit_code,
            stdout=job.stdout,
            stderr=job.stderr,
        )
