from __future__ import annotations

"""Freebuff (DeepSeek) adversarial probes - M3.3 L7 bridges + L5 router.

These probes were written red against M3.3 as shipped in 8dd0547. The findings
they named have since been closed, so the ``test_invariant_*`` cases now assert
the REQUIRED behaviour and pass - they are the regression guard for the fix.

Disposition of the review findings:

  CLOSED  F-M3.3-FB-1  path confinement now fail-closed (network/memory still open)
  CLOSED  F-M3.3-FB-2  a timeout terminates the whole process tree
  CLOSED  F-M3.3-FB-3  submit returns a LIVE handle; cancel really terminates
  CLOSED  F-M3.3-FB-4  I5 is enforced on canonical identity, not raw strings
  CLOSED  F-M3.3-FB-6  an over-limit prompt is a precondition fault, not a failure
  CLOSED  F-M3.3-FB-7  the dispatch table is synchronised; transitions are atomic
  OPEN    F-M3.3-FB-5  RoleAssignment still cannot represent attempt outcome
  OPEN    F-M3.3-FB-8  an unknown handle is still reported as a FAILED dispatch
  OPEN    F-M3.3-FB-9  provider identity is a label, not an execution boundary
  OPEN    F-M3.3-FB-10 Artifacts still carry no dispatch/worktree provenance
  OPEN    residual of FB-1: network_allowed / max_memory_mb remain unenforced
"""

import inspect
import json
import sys
import threading
import time
from pathlib import Path

import pytest

from jarvis.orchestrator.bridges import (
    AgyBridge,
    DefaultSubprocessRunner,
    OpenCodeBridge,
    PromptTooLong,
    Sandbox,
    SandboxViolation,
    WorkerStatus,
)
from jarvis.orchestrator.router import (
    Capability,
    ProviderProfile,
    Role,
    RoleAssignment,
    Router,
)

# Windows CreateProcess lpCommandLine ceiling; cmd.exe would be lower (8191).
WINDOWS_ARGV_LIMIT = 32_767


class RecordingRunner:
    """Deterministic runner seam: records (cmd, cwd, timeout), returns fixed."""

    def __init__(self, exit_code: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.calls: list[tuple[list[str], Path, float | None]] = []

    def run(self, cmd: list[str], cwd: Path, timeout: float | None = None):
        self.calls.append((list(cmd), cwd, timeout))
        return self.exit_code, self.stdout, self.stderr


class BlockingRunner:
    """Runner that blocks until released - proves dispatch really is async."""

    def __init__(self) -> None:
        self.gate = threading.Event()

    def run(self, cmd: list[str], cwd: Path, timeout: float | None = None):
        self.gate.wait(10)
        return 0, "", ""


# ---------------------------------------------------------------------------
# F-M3.3-FB-1  Sandbox path confinement is now fail-closed
# ---------------------------------------------------------------------------


def test_invariant_workdir_outside_allowed_paths_is_refused(tmp_path: Path) -> None:
    """F-M3.3-FB-1: a dispatch outside ``Sandbox.allowed_paths`` is refused
    BEFORE any worker is spawned."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    forbidden = tmp_path / "outside-allowed"
    forbidden.mkdir()
    runner = RecordingRunner()

    with pytest.raises(SandboxViolation):
        AgyBridge(runner=runner).submit(
            "do work", forbidden, Sandbox(allowed_paths=(allowed,))
        )

    assert runner.calls == [], "the worker was dispatched despite the Sandbox"


def test_invariant_workdir_inside_allowed_paths_is_dispatched(tmp_path: Path) -> None:
    """The confinement must not refuse legitimate dispatches (nesting counts)."""
    allowed = tmp_path / "allowed"
    nested = allowed / "pkg" / "worktree"
    nested.mkdir(parents=True)
    runner = RecordingRunner()

    bridge = AgyBridge(runner=runner)
    handle = bridge.submit("do work", nested, Sandbox(allowed_paths=(allowed,)))
    bridge.collect(handle)

    cmd, cwd, _timeout = runner.calls[0]
    assert cwd == nested
    assert str(nested) in cmd


def test_current_network_and_memory_sandbox_fields_remain_unenforced(
    tmp_path: Path,
) -> None:
    """RESIDUAL of F-M3.3-FB-1: ``network_allowed`` and ``max_memory_mb`` are
    still read by nothing. Tightening them cannot change any invocation, so the
    datum must not be read as a guarantee."""
    workdir = tmp_path / "work"
    workdir.mkdir()

    permissive = RecordingRunner()
    restrictive = RecordingRunner()
    a, b = OpenCodeBridge(runner=permissive), OpenCodeBridge(runner=restrictive)

    a.collect(a.submit("p", workdir, Sandbox(network_allowed=True, max_memory_mb=99999)))
    b.collect(b.submit("p", workdir, Sandbox(network_allowed=False, max_memory_mb=1)))

    assert permissive.calls == restrictive.calls


# ---------------------------------------------------------------------------
# F-M3.3-FB-2  A timeout now terminates the WHOLE process tree
# ---------------------------------------------------------------------------


def test_current_timeout_maps_to_exit_code_124(tmp_path: Path) -> None:
    """F-M3.3-FB-2 evidence: the timeout path still reports 124."""
    rc, out, err = DefaultSubprocessRunner().run(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=tmp_path,
        timeout=1.0,
    )
    assert rc == 124
    assert out == ""
    assert "TimeoutExpired" in err


def test_invariant_a_timed_out_worker_leaves_no_surviving_child_or_lock(
    tmp_path: Path,
) -> None:
    """F-M3.3-FB-2: after a timeout, no descendant survives.

    The child spawns a grandchild that holds a lock file open. Before the fix,
    ``subprocess.run(timeout=...)`` killed only the direct child: the grandchild
    kept running, and on Windows the held lock was undeletable (PermissionError)
    - the ``.git/index.lock`` failure mode that wedges the next retry.
    """
    lock_file = tmp_path / "index-lock-probe.lock"
    survived = tmp_path / "orphan-survived.txt"

    grandchild = (
        "import pathlib, time\n"
        f"fh = open(pathlib.Path(r'{lock_file}'), 'w')\n"
        "fh.write('locked')\n"
        "fh.flush()\n"
        "time.sleep(3)\n"
        "fh.close()\n"
        f"pathlib.Path(r'{survived}').write_text('survived')\n"
    )
    parent = (
        "import subprocess, sys, time\n"
        f"subprocess.Popen([sys.executable, '-c', {grandchild!r}],\n"
        "                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,\n"
        "                 stderr=subprocess.DEVNULL)\n"
        "time.sleep(30)\n"
    )

    rc, _out, err = DefaultSubprocessRunner().run(
        [sys.executable, "-c", parent], cwd=tmp_path, timeout=1.0
    )
    assert rc == 124, f"expected the timeout path, got rc={rc} err={err!r}"

    try:
        # The grandchild opened the lock before the kill. If it is really gone,
        # the lock is immediately removable (Windows only signal).
        lock_deletable: bool | None = None
        if lock_file.exists():
            try:
                lock_file.unlink()
                lock_deletable = True
            except PermissionError:
                lock_deletable = False

        deadline = time.time() + 4
        while time.time() < deadline and not survived.exists():
            time.sleep(0.1)
        orphaned = survived.exists()

        assert not orphaned, (
            "F-M3.3-FB-2: a timed-out worker's grandchild kept running after the "
            f"parent was killed. lock_deletable={lock_deletable}"
        )
        if sys.platform == "win32" and lock_deletable is not None:
            assert lock_deletable, (
                "F-M3.3-FB-2: the lock is still held after the whole tree should "
                "have been terminated"
            )
    finally:
        try:
            lock_file.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# F-M3.3-FB-3  submit/status/cancel is now a real asynchronous dispatch
# ---------------------------------------------------------------------------


def test_invariant_submit_hands_back_a_live_handle_while_the_worker_runs(
    tmp_path: Path,
) -> None:
    """F-M3.3-FB-3: submit() returns a LIVE handle; the worker is still running."""
    runner = BlockingRunner()
    bridge = OpenCodeBridge(runner=runner)
    returned: dict = {}

    worker = threading.Thread(
        target=lambda: returned.__setitem__(
            "handle", bridge.submit("p", tmp_path, Sandbox())
        ),
        daemon=True,
    )
    worker.start()
    time.sleep(0.3)
    try:
        assert "handle" in returned, (
            "F-M3.3-FB-3: submit() did not return while the worker was running - "
            "the dispatch is not asynchronous"
        )
        assert bridge.status(returned["handle"]) is WorkerStatus.RUNNING
    finally:
        runner.gate.set()
        worker.join(10)


def test_invariant_cancel_terminates_an_in_flight_dispatch(tmp_path: Path) -> None:
    """F-M3.3-FB-3: cancel() reaches the in-flight dispatch and settles it
    CANCELLED, rather than being unreachable dead code."""
    runner = BlockingRunner()
    bridge = OpenCodeBridge(runner=runner)
    handle = bridge.submit("p", tmp_path, Sandbox())

    assert bridge.status(handle) is WorkerStatus.RUNNING
    bridge.cancel(handle)
    assert bridge.status(handle) is WorkerStatus.CANCELLED

    runner.gate.set()  # let the (unstoppable) injected runner unwind
    artifacts = bridge.collect(handle)
    assert bridge.status(handle) is WorkerStatus.CANCELLED
    assert artifacts.stderr != "dispatch still running"


def test_invariant_a_cancelled_dispatch_is_not_reported_as_completed(
    tmp_path: Path,
) -> None:
    """cancel() must not be clobbered by a worker that would have exited 0."""
    runner = BlockingRunner()
    bridge = OpenCodeBridge(runner=runner)
    handle = bridge.submit("p", tmp_path, Sandbox())

    assert bridge.status(handle) is WorkerStatus.RUNNING
    bridge.cancel(handle)
    runner.gate.set()  # the worker now returns exit code 0
    bridge.collect(handle)

    assert bridge.status(handle) is WorkerStatus.CANCELLED


def test_invariant_dispatch_state_is_synchronised() -> None:
    """F-M3.3-FB-7: the job table is guarded and every transition is a single
    lock-protected swap, so a polling scheduler can share it safely."""
    import jarvis.orchestrator.bridges.dispatch as dispatch_mod
    import jarvis.orchestrator.bridges.process as process_mod

    dispatch_src = inspect.getsource(dispatch_mod)
    assert "threading.RLock()" in dispatch_src
    assert "with self._lock:" in dispatch_src

    process_src = inspect.getsource(process_mod)
    assert "threading.Lock()" in process_src


# ---------------------------------------------------------------------------
# F-M3.3-FB-4  Invariant I5 is enforced on canonical identity
# ---------------------------------------------------------------------------


def test_invariant_i5_survives_provider_name_case_variant() -> None:
    """F-M3.3-FB-4: a case variant must not evade the exclusion."""
    router = Router()
    prior = [
        RoleAssignment(
            package="M3.3", role=Role.RED_TEAM_REVIEWER, provider="Antigravity"
        )
    ]
    result = router.resolve(Role.INDEPENDENT_VERIFIER, package="M3.3", assignments=prior)
    assert not result.ok and result.degraded, (
        f"F-M3.3-FB-4: antigravity red-teamed and then verified M3.3 -> {result}"
    )


def test_invariant_i5_survives_provider_aliasing() -> None:
    """F-M3.3-FB-4: an alias for the same logical worker must be excluded too."""
    registry = {
        "antigravity": ProviderProfile(
            name="antigravity",
            capabilities=frozenset({Capability.VERIFICATION_V1}),
            priority=30,
        ),
        "agy": ProviderProfile(
            name="agy",
            capabilities=frozenset({Capability.VERIFICATION_V1}),
            priority=10,
        ),
    }
    prior = [
        RoleAssignment(
            package="M3.3", role=Role.RED_TEAM_REVIEWER, provider="antigravity"
        )
    ]
    result = Router(registry=registry).resolve(
        Role.INDEPENDENT_VERIFIER, package="M3.3", assignments=prior
    )
    assert not result.ok, (
        f"F-M3.3-FB-4: alias 'agy' filled verification after antigravity "
        f"red-teamed the same package -> {result}"
    )


def test_invariant_i5_survives_package_name_case_variant() -> None:
    """F-M3.3-FB-4: the exclusion is scoped by canonical package id."""
    router = Router()
    prior = [
        RoleAssignment(
            package="m3.3", role=Role.RED_TEAM_REVIEWER, provider="antigravity"
        )
    ]
    result = router.resolve(Role.INDEPENDENT_VERIFIER, package="M3.3", assignments=prior)
    assert not result.ok, (
        f"F-M3.3-FB-4: package-string case variant defeated I5 -> {result}"
    )


def test_invariant_i5_still_allows_a_genuinely_different_provider() -> None:
    """Canonicalization must not over-exclude: a different provider is allowed."""
    router = Router()
    prior = [
        RoleAssignment(
            package="M3.3", role=Role.RED_TEAM_REVIEWER, provider="freebuff"
        )
    ]
    result = router.resolve(Role.INDEPENDENT_VERIFIER, package="M3.3", assignments=prior)
    assert result.ok and result.provider == "antigravity"


def test_open_i5_cannot_distinguish_a_failed_attempt_from_rejected_history() -> None:
    """STILL OPEN (F-M3.3-FB-5): ``RoleAssignment`` carries {package, role,
    provider} only - no attempt id, no outcome. A red-team run that FAILED and
    produced nothing still permanently excludes that provider from verifying the
    same package, and a caller has no vocabulary to re-allow it."""
    assert set(RoleAssignment.__dataclass_fields__) == {"package", "role", "provider"}

    router = Router()
    prior = [
        RoleAssignment(
            package="M3.3", role=Role.RED_TEAM_REVIEWER, provider="antigravity"
        )
    ]
    assert not router.resolve(
        Role.INDEPENDENT_VERIFIER, package="M3.3", assignments=prior
    ).ok


# ---------------------------------------------------------------------------
# F-M3.3-FB-6  Prompt length is a precondition fault, not a worker failure
# ---------------------------------------------------------------------------


def test_invariant_an_overlong_prompt_is_rejected_before_dispatch(
    tmp_path: Path,
) -> None:
    """F-M3.3-FB-6: past the platform argv ceiling the spawn itself would fail,
    and that failure was indistinguishable from a worker that ran and failed -
    so the recovery ladder burned every bounded attempt on an unfixable fault."""
    runner = RecordingRunner(
        exit_code=1, stderr="[WinError 206] The filename or extension is too long"
    )
    bridge = OpenCodeBridge(runner=runner)
    huge = "x" * (WINDOWS_ARGV_LIMIT + 8192)

    with pytest.raises(PromptTooLong):
        bridge.submit(huge, tmp_path, Sandbox())

    assert runner.calls == [], "an over-limit prompt reached the worker"


def test_open_a_spawn_fault_is_still_reported_as_a_worker_failure(
    tmp_path: Path,
) -> None:
    """STILL OPEN (residual of F-M3.3-FB-6): at the Runner layer a spawn fault is
    still flattened into ``(1, '', err)``. The bridge now guards the length, so
    only non-length spawn faults reach here - but they remain indistinguishable
    from a worker failure."""
    rc, out, err = DefaultSubprocessRunner().run(
        [sys.executable, "-c", "print('x')", "y" * (WINDOWS_ARGV_LIMIT + 8192)],
        cwd=tmp_path,
        timeout=30,
    )
    assert rc == 1
    assert out == ""
    assert "206" in err or "too long" in err.lower(), err


def test_current_prompt_round_trips_through_argv_for_a_python_child(
    tmp_path: Path,
) -> None:
    """No-findings surface: hostile prompt bytes (quotes, backslashes, newline,
    non-ASCII, trailing backslash) survive the argv round trip for a child that
    parses with the same convention - ``shell=False`` with a list argument."""
    tricky = 'quote " backslash \\ newline\nunicode \u00e9 trailing \\'
    child = "import json,sys;print(json.dumps(sys.argv[1]))"

    rc, out, err = DefaultSubprocessRunner().run(
        [sys.executable, "-c", child, tricky], cwd=tmp_path, timeout=30
    )
    assert rc == 0, err
    assert json.loads(out.strip()) == tricky


# ---------------------------------------------------------------------------
# F-M3.3-FB-8  Unknown handles (still open)
# ---------------------------------------------------------------------------


def test_open_unknown_handle_is_silently_reported_as_a_failure(
    tmp_path: Path,
) -> None:
    """STILL OPEN (F-M3.3-FB-8): job state is per-instance and in-memory. A
    handle from a previous process - e.g. after the M3.5 daemon restarts - reads
    as FAILED and ``collect()`` fabricates ``exit_code=1``: indistinguishable
    from a worker that genuinely failed."""
    runner = RecordingRunner(exit_code=0)
    bridge_a = OpenCodeBridge(runner=runner)
    handle = bridge_a.submit("p", tmp_path, Sandbox())
    bridge_a.collect(handle)
    assert bridge_a.status(handle) is WorkerStatus.COMPLETED

    bridge_b = OpenCodeBridge(runner=runner)
    assert bridge_b.status(handle) is WorkerStatus.FAILED
    artifacts = bridge_b.collect(handle)
    assert artifacts.exit_code == 1
    assert "Unknown handle" in artifacts.stderr
