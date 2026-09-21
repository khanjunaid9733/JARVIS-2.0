from __future__ import annotations

"""L7 Bridges Package (ORCHESTRATOR_ARCHITECTURE.md section 12).

Provides bridge adapters to external worker environments:
- OpenCodeBridge (Big Pickle)
- AgyBridge (Antigravity)
- DeepSeekBridge (Freebuff)

Every adapter shares ONE dispatch lifecycle (``dispatch.WorkerDispatch``) and ONE
process-containment implementation (``process.ContainedProcess``).
"""

from .agy import AgyBridge
from .deepseek import DeepSeekBridge
from .dispatch import (
    ARGV_LIMIT_POSIX,
    ARGV_LIMIT_WINDOWS,
    WorkerDispatch,
    argv_limit,
    validate_dispatch,
)
from .opencode import OpenCodeBridge
from .process import ContainedProcess, DefaultSubprocessRunner
from .protocol import (
    Artifacts,
    Bridge,
    BridgeError,
    CommandRunner,
    Handle,
    PromptTooLong,
    Sandbox,
    SandboxViolation,
    WorkerStatus,
)

__all__ = [
    "ARGV_LIMIT_POSIX",
    "ARGV_LIMIT_WINDOWS",
    "AgyBridge",
    "Artifacts",
    "Bridge",
    "BridgeError",
    "CommandRunner",
    "ContainedProcess",
    "DeepSeekBridge",
    "DefaultSubprocessRunner",
    "Handle",
    "OpenCodeBridge",
    "PromptTooLong",
    "Sandbox",
    "SandboxViolation",
    "WorkerDispatch",
    "WorkerStatus",
    "argv_limit",
    "validate_dispatch",
]
