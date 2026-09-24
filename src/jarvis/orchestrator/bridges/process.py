from __future__ import annotations

"""Process containment for L7 workers (closes F-M3.3-FB-2).

The previous default runner used ``subprocess.run(timeout=...)``, which kills
only the DIRECT child. Descendants survived the timeout, kept worktree locks
open, and on Windows made those locks undeletable - so the next retry could not
clean the worktree and the bounded recovery ladder spent every attempt on a
fault no retry could fix. That was reproduced, not hypothesised: an orphaned
grandchild holding a lock file made ``Path.unlink`` raise ``PermissionError``
after the parent had been killed.

Every worker is now spawned inside a containment boundary, so the WHOLE tree
can be terminated:

  * Windows - a Job Object with ``JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE``. The tree
    is terminated with ``TerminateJobObject``; closing the job handle reaps any
    descendant that outlived the child. If job creation or assignment is
    unavailable the boundary degrades to ``taskkill /F /T``.
  * POSIX - a new session (``start_new_session=True``), terminated with
    ``killpg(SIGKILL)``.

This is the ONE spawn/wait/terminate implementation. The three near-identical
copies that lived in ``opencode.py`` / ``agy.py`` / ``deepseek.py`` are gone.
"""

import os
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path
from typing import Sequence

WINDOWS = sys.platform == "win32"

# The run/collect contract keeps the POSIX-ish 124 for "timed out", so a caller
# can tell a timeout from a worker that ran and failed by exit code alone.
TIMEOUT_EXIT_CODE = 124
_GRACE_SECONDS = 5.0

_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_PROCESS_TERMINATE = 0x0001
_PROCESS_SET_QUOTA = 0x0100


if WINDOWS:  # pragma: no cover - exercised on Windows only
    import ctypes
    from ctypes import wintypes

    class _LARGE_INTEGER(ctypes.Structure):
        _fields_ = [("QuadPart", ctypes.c_longlong)]

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", _LARGE_INTEGER),
            ("PerJobUserTimeLimit", _LARGE_INTEGER),
            ("LimitFlags", ctypes.c_uint32),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_uint32),
            ("Affinity", ctypes.POINTER(ctypes.c_ulong)),
            ("PriorityClass", ctypes.c_uint32),
            ("SchedulingClass", ctypes.c_uint32),
        ]

    class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]


class _WindowsJob:
    """A kill-on-close Job Object owning one worker and all of its descendants."""

    def __init__(self) -> None:  # pragma: no cover - Windows only
        self._k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._configure_signatures()
        self.handle = self._k32.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError("CreateJobObjectW failed")
        info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        ok = self._k32.SetInformationJobObject(
            self.handle,
            _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
            ctypes.byref(info),
            ctypes.sizeof(info),
        )
        if not ok:
            self.close()
            raise OSError("SetInformationJobObject failed")

    def _configure_signatures(self) -> None:  # pragma: no cover - Windows only
        k32 = self._k32
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
        k32.SetInformationJobObject.restype = wintypes.BOOL
        k32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
        ]
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.AssignProcessToJobObject.restype = wintypes.BOOL
        k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        k32.TerminateJobObject.restype = wintypes.BOOL
        k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        k32.CloseHandle.restype = wintypes.BOOL
        k32.CloseHandle.argtypes = [wintypes.HANDLE]

    def assign(self, pid: int) -> bool:  # pragma: no cover - Windows only
        """Put an already-running process (and future children) inside the job."""
        handle = self._k32.OpenProcess(
            _PROCESS_TERMINATE | _PROCESS_SET_QUOTA, False, pid
        )
        if not handle:
            return False
        try:
            return bool(self._k32.AssignProcessToJobObject(self.handle, handle))
        finally:
            self._k32.CloseHandle(handle)

    def terminate(self) -> None:  # pragma: no cover - Windows only
        if self.handle:
            try:
                self._k32.TerminateJobObject(self.handle, 1)
            except OSError:
                pass

    def close(self) -> None:  # pragma: no cover - Windows only
        if self.handle:
            try:
                self._k32.CloseHandle(self.handle)
            except OSError:
                pass
            self.handle = None


def _resolve_launch_command(cmd: Sequence[str]) -> list[str]:
    """Resolve ``argv[0]`` the way a shell would, so a shim is launchable.

    ``CreateProcess`` appends only ``.exe`` to a bare name, so an
    npm-installed CLI that is on PATH as ``opencode`` (a POSIX sh shim) and
    ``opencode.CMD`` - but with no ``opencode.exe`` - made every dispatch die
    with ``FileNotFoundError [WinError 2]``. The engine looked absent when it
    was only unlaunchable. ``shutil.which`` honours ``PATHEXT``, so the launch
    now matches what the user's shell does. Measured on this host: the bare
    name raised WinError 2; the resolved ``.CMD`` spawned a live process.
    """
    argv = list(cmd)
    if not argv:
        return argv
    resolved = shutil.which(argv[0])
    if resolved is not None:
        argv[0] = resolved
    return argv


def _taskkill_tree(pid: int | None) -> None:
    """Last-resort descendant kill when no job boundary could be established."""
    if pid is None:
        return
    try:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            shell=False,
            timeout=_GRACE_SECONDS,
        )
    except Exception:  # noqa: BLE001 - best effort by definition
        pass


class ContainedProcess:
    """One worker process plus the containment that owns its descendants."""

    def __init__(self, cmd: Sequence[str], cwd: Path) -> None:
        self.cmd = list(cmd)
        self.cwd = Path(cwd)
        self._proc: subprocess.Popen[str] | None = None
        self._job: _WindowsJob | None = None
        self._lock = threading.Lock()

    @property
    def pid(self) -> int | None:
        return self._proc.pid if self._proc is not None else None

    def start(self) -> ContainedProcess:
        """Spawn the worker inside its containment boundary."""
        if WINDOWS:  # pragma: no cover - Windows only
            try:
                self._job = _WindowsJob()
            except Exception:  # noqa: BLE001 - containment degrades, never blocks
                self._job = None
            self._proc = self._popen()
            if self._job is not None and not self._job.assign(self._proc.pid):
                self._job.close()
                self._job = None
        else:
            self._proc = self._popen(start_new_session=True)
        return self

    def _popen(self, start_new_session: bool = False) -> subprocess.Popen[str]:
        return subprocess.Popen(
            _resolve_launch_command(self.cmd),
            cwd=str(self.cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            start_new_session=start_new_session,
        )

    def wait(self, timeout: float | None = None) -> tuple[int, str, str]:
        """Block until the worker (or its timeout) resolves; always reap the tree.

        Returns ``(exit_code, stdout, stderr)``. ``TIMEOUT_EXIT_CODE`` is
        returned - and the WHOLE tree terminated - when ``timeout`` elapses.
        """
        proc = self._proc
        if proc is None:
            raise RuntimeError("ContainedProcess.wait called before start()")
        try:
            out, err = proc.communicate(timeout=timeout)
            return proc.returncode, out or "", err or ""
        except subprocess.TimeoutExpired:
            self.terminate()
            try:
                out, err = proc.communicate(timeout=_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                self.kill()
                out, err = "", ""
            return TIMEOUT_EXIT_CODE, out or "", (err or "") + "\nTimeoutExpired"
        finally:
            self.close()

    def terminate(self) -> None:
        """Terminate the worker AND every descendant it spawned."""
        with self._lock:
            proc, job = self._proc, self._job
        if proc is None or proc.poll() is not None:
            return
        if WINDOWS:  # pragma: no cover - Windows only
            # The Job Object owns only descendants created AFTER assign(pid).
            # A child spawned in the _popen->assign window escapes it, so the
            # tree walk must run FIRST, from the live parent PID - it traverses
            # the real process tree regardless of job membership.
            _taskkill_tree(proc.pid)
            if job is not None:
                job.terminate()
            self.kill()
            return
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            self.kill()

    def kill(self) -> None:
        """Terminate only the direct child (the backstop path)."""
        proc = self._proc
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass

    def close(self) -> None:
        """Release the containment, which reaps any lingering descendant."""
        with self._lock:
            job = self._job
            self._job = None
        if job is not None:
            job.terminate()
            job.close()


class DefaultSubprocessRunner:
    """Default ``CommandRunner``: every worker runs inside a containment boundary.

    Implements both the blocking ``run`` seam (used by the bridges' injected
    runners) and the ``start``/``terminate`` pair, which lets an asynchronous
    dispatch hold the live process itself - giving a real ``Handle.process_id``
    and a ``cancel()`` that actually stops the tree.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current: ContainedProcess | None = None

    def start(self, cmd: Sequence[str], cwd: Path) -> ContainedProcess:
        process = ContainedProcess(cmd, cwd).start()
        with self._lock:
            self._current = process
        return process

    def run(
        self, cmd: Sequence[str], cwd: Path, timeout: float | None = None
    ) -> tuple[int, str, str]:
        try:
            process = self.start(cmd, cwd)
        except Exception as exc:  # noqa: BLE001 - a spawn fault is a datum, not a crash
            return 1, "", f"{type(exc).__name__}: {exc}"
        try:
            return process.wait(timeout)
        finally:
            with self._lock:
                if self._current is process:
                    self._current = None

    def terminate(self) -> None:
        with self._lock:
            process = self._current
        if process is not None:
            process.terminate()


__all__ = [
    "ContainedProcess",
    "DefaultSubprocessRunner",
    "TIMEOUT_EXIT_CODE",
    "WINDOWS",
]
