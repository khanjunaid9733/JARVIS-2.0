from __future__ import annotations

"""L7 Bridge Protocols & Datums (ORCHESTRATOR_ARCHITECTURE.md §12).

Defines the unverified boundary between the deterministic decision plane and
external untrusted LLM workers (OpenCode, Antigravity, DeepSeek).

All bridges implement the `Bridge` protocol:
    submit  -> schedule execution in isolated worktree with sandbox constraints
    status  -> poll current lifecycle status (PENDING/RUNNING/COMPLETED/FAILED/CANCELLED)
    cancel  -> gracefully terminate execution
    collect -> retrieve machine-readable artifacts and execution output
"""

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class WorkerStatus(str, enum.Enum):
    """Execution status of an external bridge worker."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class Sandbox:
    """Capability boundaries and resource limits for worker execution."""

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
    """Hermetic injection seam for subprocess execution."""

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
