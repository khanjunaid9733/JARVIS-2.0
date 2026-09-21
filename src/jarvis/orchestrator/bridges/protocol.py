from __future__ import annotations

"""L7 Bridge Protocols & Datums (ORCHESTRATOR_ARCHITECTURE.md section 12).

Defines the unverified boundary between the deterministic decision plane and
external untrusted LLM workers (OpenCode, Antigravity, DeepSeek).

All bridges implement the `Bridge` protocol:
    submit  -> validate, spawn in a containment boundary, return a LIVE handle
    status  -> non-blocking poll (PENDING/RUNNING/COMPLETED/FAILED/CANCELLED)
    cancel  -> terminate the dispatch AND its process tree
    collect -> wait for termination, then retrieve artifacts

The decision plane never trusts a worker's completion claim; it reads returned
artifacts and hands them to the Verification Authority (L0).
"""

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class BridgeError(Exception):
    """Base class for bridge faults that are NOT worker failures.

    These are precondition faults: the dispatch never happened, so a caller must
    not route them into the recovery ladder as if a worker had run and failed.
    """


class PromptTooLong(BridgeError):
    """The prompt cannot fit in a platform argument vector (F-M3.3-FB-6)."""


class SandboxViolation(BridgeError):
    """The dispatch targets a path outside the declared Sandbox (F-M3.3-FB-1)."""


class WorkerStatus(str, enum.Enum):
    """Execution status of an external bridge worker."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class Sandbox:
    """Capability boundaries and resource limits for worker execution.

    Enforcement, stated plainly so the datum cannot be mistaken for a guarantee
    (F-M3.3-FB-1):

    * ``allowed_paths`` - ENFORCED when non-empty (see ``validate_dispatch``).
      An empty tuple means "no path constraint declared", which is the
      historical default.
    * ``timeout_seconds`` - ENFORCED; on expiry the whole process tree is
      terminated (F-M3.3-FB-2).
    * ``network_allowed`` / ``max_memory_mb`` - NOT ENFORCED. They are recorded
      here and flagged in review; nothing reads them yet.
    """

    allowed_paths: tuple[Path, ...] = field(default_factory=tuple)
    timeout_seconds: float = 300.0
    network_allowed: bool = False
    max_memory_mb: int = 4096


@dataclass(frozen=True)
class Handle:
    """Opaque handle representing an in-flight or finished worker dispatch."""

    handle_id: str
    workdir: Path
    process_id: int | None = None
    started_at: str = ""


@dataclass(frozen=True)
class Artifacts:
    """Collected outputs and exit state from a completed worker run."""

    exit_code: int
    stdout: str
    stderr: str
    output_files: tuple[Path, ...] = field(default_factory=tuple)


class CommandRunner(Protocol):
    """Hermetic injection seam for subprocess execution.

    The only required member is ``run``. A runner MAY additionally implement
    ``start(cmd, cwd) -> process`` and ``terminate()``; when it does, the
    dispatch holds the live process directly, so ``Handle.process_id`` is real
    and ``cancel()`` reaches the process tree. Runners without those members are
    driven through ``run`` in a worker thread and cancellation degrades to
    marking the dispatch cancelled.
    """

    def run(
        self, cmd: list[str], cwd: Path, timeout: float | None = None
    ) -> tuple[int, str, str]: ...


class Bridge(Protocol):
    """The unverified bridge seam (L7).

    Bridges communicate with external worker tools. The decision plane never
    trusts a worker's completion claim; it only reads returned artifacts
    and hands them to the Verification Authority (L0).
    """

    def submit(self, prompt: str, workdir: Path, sandbox: Sandbox) -> Handle: ...

    def status(self, handle: Handle) -> WorkerStatus: ...

    def cancel(self, handle: Handle) -> None: ...

    def collect(self, handle: Handle) -> Artifacts: ...


__all__ = [
    "Artifacts",
    "Bridge",
    "BridgeError",
    "CommandRunner",
    "Handle",
    "PromptTooLong",
    "Sandbox",
    "SandboxViolation",
    "WorkerStatus",
]
