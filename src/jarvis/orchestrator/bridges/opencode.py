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

    def __init__(
        self,
        runner: object | None = None,
        provider_model: str | None = None,
        auto_approve: bool = False,
    ) -> None:
        super().__init__(runner=runner)
        self._provider_model = provider_model
        self._auto_approve = auto_approve

    def _argv(self, prompt: str, workdir: Path) -> list[str]:
        del workdir  # opencode receives its working directory via cwd
        cmd = ["opencode", "run"]
        if self._auto_approve:
            cmd.append("--auto")
        if self._provider_model:
            cmd.extend(["-m", self._provider_model])
        cmd.append(prompt)
        return cmd


__all__ = ["OpenCodeBridge"]

