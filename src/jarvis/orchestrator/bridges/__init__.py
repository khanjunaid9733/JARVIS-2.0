from __future__ import annotations

"""L7 Bridges Package (ORCHESTRATOR_ARCHITECTURE.md §12).

Provides bridge adapters to external worker environments:
- OpenCodeBridge (Big Pickle)
- AgyBridge (Antigravity)
- DeepSeekBridge (Freebuff)
"""

from .agy import AgyBridge
from .deepseek import DeepSeekBridge
from .opencode import OpenCodeBridge
from .protocol import (
    Artifacts,
    Bridge,
    CommandRunner,
    Handle,
    Sandbox,
    WorkerStatus,
)

__all__ = [
    "AgyBridge",
    "Artifacts",
    "Bridge",
    "CommandRunner",
    "DeepSeekBridge",
    "Handle",
    "OpenCodeBridge",
    "Sandbox",
    "WorkerStatus",
]
