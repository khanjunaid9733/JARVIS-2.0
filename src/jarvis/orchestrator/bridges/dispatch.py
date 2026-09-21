from __future__ import annotations

"""Shared dispatch preconditions and lifecycle for every L7 bridge.

Closes three review findings at once:

  * **F-M3.3-FB-1** - ``validate_dispatch`` is fail-closed on the boundary the
    Sandbox actually declares: a workdir outside every ``allowed_paths`` entry
    is refused BEFORE any worker is spawned.
  * **F-M3.3-FB-3** - ``submit`` now spawns and returns a LIVE handle
    immediately. ``status`` observes RUNNING, ``cancel`` really terminates the
    tree, ``collect`` waits for the dispatch to terminate before claiming
    artifacts. Previously all of that was one blocking call.
  * **F-M3.3-FB-7** - the job table is synchronised and every transition is a
    single lock-protected swap.

It is the ONE lifecycle implementation. The three copies that lived in
``opencode.py`` / ``agy.py`` / ``deepseek.py`` are gone.

Residual, reported and NOT silently implied: ``Sandbox.network_allowed`` and
``Sandbox.max_memory_mb`` are still not enforced, and an unresolvable handle is
still reported as a FAILED dispatch (F-M3.3-FB-8).
"""

import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .process import ContainedProcess, DefaultSubprocessRunner
from .protocol import (
    Artifacts,
    Handle,
    PromptTooLong,
    Sandbox,
    SandboxViolation,
    WorkerStatus,
)

# Conservative argv ceilings. Windows caps the whole CreateProcess command line
# at 32767 characters; POSIX caps a single argv string at MAX_ARG_STRLEN
# (131072 on Linux). A prompt beyond the ceiling makes the SPAWN fail, and that
# failure is indistinguishable from a worker failure once it reaches the ladder
# - so it must be a precondition fault, not a dispatch. (F-M3.3-FB-6)
ARGV_LIMIT_WINDOWS = 30_000
ARGV_LIMIT_POSIX = 131_072

_COLLECT_GRACE_SECONDS = 5.0


def argv_limit(platform_name: str | None = None) -> int:
    """The prompt/argv ceiling for a platform name (defaults to the real one)."""
    import sys

    name = platform_name if platform_name is not None else sys.platform
    return ARGV_LIMIT_WINDOWS if name.startswith("win") else ARGV_LIMIT_POSIX


def validate_dispatch(prompt: str, workdir: Path, sandbox: Sandbox) -> Path:
    """Fail-closed preconditions for one worker dispatch; returns the workdir.

    Raises ``PromptTooLong`` when the prompt cannot fit in an argument vector,
    and ``SandboxViolation`` when the workdir lies outside every
    ``sandbox.allowed_paths`` entry.

    An EMPTY ``allowed_paths`` tuple means "no path constraint declared". That is
    the historical default and is preserved so existing callers keep working; a
    non-empty tuple is enforced.
    """
    limit = argv_limit()
    if len(prompt) > limit:
        raise PromptTooLong(
            f"prompt is {len(prompt)} characters; this platform's argv ceiling is "
            f"{limit}. Dispatch it by file reference instead - the spawn would "
            "otherwise fail and be reported as a worker failure"
        )

    workdir_path = Path(workdir)
    resolved = workdir_path.resolve()
    if sandbox.allowed_paths:
        allowed = [Path(p).resolve() for p in sandbox.allowed_paths]
        if not any(resolved.is_relative_to(root) for root in allowed):
            raise SandboxViolation(
                f"workdir {resolved} is outside Sandbox.allowed_paths "
                f"{[str(root) for root in allowed]}"
            )
    # The ORIGINAL path is returned: containment is checked on the resolved
    # form, but the dispatch must keep handing the caller's path through byte
    # for byte (existing command-line assertions depend on it).
    return workdir_path


@dataclass
class _Job:
    """Mutable status of one in-flight dispatch, guarded by WorkerDispatch._lock."""

    status: WorkerStatus
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    cancelled: bool = False
    timeout: float = 300.0
    process: ContainedProcess | None = None
    thread: threading.Thread | None = None


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class WorkerDispatch:
    """The asynchronous dispatch lifecycle every L7 bridge shares."""

    handle_prefix: str = "worker"

    def __init__(self, runner: object | None = None) -> None:
        self._runner = runner if runner is not None else DefaultSubprocessRunner()
        self._lock = threading.RLock()
        self._jobs: dict[str, _Job] = {}

    # -- subclass seam -------------------------------------------------------

    def _argv(self, prompt: str, workdir: Path) -> list[str]:
        """The argument vector that runs this provider's worker."""
        raise NotImplementedError

    # -- public API (ORCHESTRATOR_ARCHITECTURE.md section 12) ----------------

    def submit(self, prompt: str, workdir: Path, sandbox: Sandbox) -> Handle:
        """Validate, spawn, and return a LIVE handle - never block on the worker."""
        target_dir = validate_dispatch(prompt, workdir, sandbox)
        argv = self._argv(prompt, target_dir)
        handle_id = f"{self.handle_prefix}-{uuid.uuid4().hex[:12]}"
        job = _Job(status=WorkerStatus.PENDING, timeout=sandbox.timeout_seconds)
        with self._lock:
            self._jobs[handle_id] = job

        start = getattr(self._runner, "start", None)
        if callable(start):
            process = start(argv, target_dir)
            job.process = process
            process_id: int | None = process.pid
            target, args = self._await, (job, process)
        else:
            process_id = None
            target, args = self._execute, (job, argv, target_dir)

        handle = Handle(
            handle_id=handle_id,
            workdir=target_dir,
            process_id=process_id,
            started_at=_utc_now(),
        )
        with self._lock:
            job.status = WorkerStatus.RUNNING
            thread = threading.Thread(
                target=target, args=args, name=handle_id, daemon=True
            )
            job.thread = thread
        thread.start()
        return handle

    def status(self, handle: Handle) -> WorkerStatus:
        with self._lock:
            job = self._jobs.get(handle.handle_id)
            if job is None:
                return WorkerStatus.FAILED
            return job.status

    def cancel(self, handle: Handle) -> None:
        """Terminate the dispatch AND its process tree; idempotent."""
        with self._lock:
            job = self._jobs.get(handle.handle_id)
            if job is None or job.status not in (
                WorkerStatus.PENDING,
                WorkerStatus.RUNNING,
            ):
                return
            job.cancelled = True
            job.status = WorkerStatus.CANCELLED
            process = job.process
        if process is not None:
            process.terminate()
            return
        terminate = getattr(self._runner, "terminate", None)
        if callable(terminate):
            terminate()

    def collect(self, handle: Handle) -> Artifacts:
        """Wait for the dispatch to terminate, then return its artifacts."""
        with self._lock:
            job = self._jobs.get(handle.handle_id)
        if job is None:
            return Artifacts(exit_code=1, stdout="", stderr="Unknown handle")

        thread = job.thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(job.timeout + _COLLECT_GRACE_SECONDS)

        with self._lock:
            if job.status in (WorkerStatus.PENDING, WorkerStatus.RUNNING):
                return Artifacts(
                    exit_code=1,
                    stdout=job.stdout,
                    stderr="dispatch still running",
                )
            return Artifacts(
                exit_code=job.exit_code, stdout=job.stdout, stderr=job.stderr
            )

    # -- internals -----------------------------------------------------------

    def _await(self, job: _Job, process: ContainedProcess) -> None:
        try:
            code, out, err = process.wait(job.timeout)
        except Exception as exc:  # noqa: BLE001 - a fault is a datum, not a crash
            code, out, err = 1, "", f"{type(exc).__name__}: {exc}"
        self._settle(job, code, out, err)

    def _execute(self, job: _Job, argv: Sequence[str], resolved: Path) -> None:
        try:
            code, out, err = self._runner.run(  # type: ignore[attr-defined]
                list(argv), cwd=resolved, timeout=job.timeout
            )
        except Exception as exc:  # noqa: BLE001 - a fault is a datum, not a crash
            code, out, err = 1, "", f"{type(exc).__name__}: {exc}"
        self._settle(job, code, out, err)

    def _settle(self, job: _Job, code: int, out: str, err: str) -> None:
        with self._lock:
            job.exit_code, job.stdout, job.stderr = code, out, err
            if job.cancelled:
                job.status = WorkerStatus.CANCELLED
            elif code == 0:
                job.status = WorkerStatus.COMPLETED
            else:
                job.status = WorkerStatus.FAILED


__all__ = [
    "ARGV_LIMIT_POSIX",
    "ARGV_LIMIT_WINDOWS",
    "WorkerDispatch",
    "argv_limit",
    "validate_dispatch",
]
