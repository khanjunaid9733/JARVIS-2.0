from __future__ import annotations

"""OpenCode (Big Pickle) L7 Bridge (ORCHESTRATOR_ARCHITECTURE.md section 12).

Runs tasks through the OpenCode CLI (``opencode run "<prompt>"``). All
validation, spawning, containment and lifecycle handling live in the shared
``dispatch`` module - this file is only the provider's argument vector.
"""

from pathlib import Path

from .dispatch import WorkerDispatch


class OpenCodeBridge(WorkerDispatch):
    """Bridge adapter for OpenCode / Big Pickle workers."""

    handle_prefix = "opencode"

    def _argv(self, prompt: str, workdir: Path) -> list[str]:
        del workdir  # opencode receives its working directory via cwd
        return ["opencode", "run", prompt]


__all__ = ["OpenCodeBridge"]
