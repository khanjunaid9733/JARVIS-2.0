from __future__ import annotations

"""Antigravity (AGY) L7 Bridge (ORCHESTRATOR_ARCHITECTURE.md section 12).

Runs tasks through the Antigravity headless CLI:

    agy -p "<prompt>" --dangerously-skip-permissions --add-dir "<workdir>"

All validation, spawning, containment and lifecycle handling live in the shared
``dispatch`` module - this file is only the provider's argument vector.

Known open item, unchanged by this pass: ``ORCHESTRATOR_ARCHITECTURE.md:257``
states the Sandbox "replaces ``--dangerously-skip-permissions`` entirely", and
that flag is still passed here. Removing it changes how the real CLI behaves,
so it is a creator decision rather than a silent edit.
"""

from pathlib import Path

from .dispatch import WorkerDispatch


class AgyBridge(WorkerDispatch):
    """Bridge adapter for Antigravity (AGY) workers."""

    handle_prefix = "agy"

    def _argv(self, prompt: str, workdir: Path) -> list[str]:
        return [
            "agy",
            "-p",
            prompt,
            "--dangerously-skip-permissions",
            "--add-dir",
            str(workdir),
        ]


__all__ = ["AgyBridge"]
