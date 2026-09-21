from __future__ import annotations

"""DeepSeek (Freebuff) L7 Bridge (ORCHESTRATOR_ARCHITECTURE.md section 12).

Runs adversarial red-team review tasks by selecting a model through the OpenCode
runner. All validation, spawning, containment and lifecycle handling live in the
shared ``dispatch`` module - this file is only the provider's argument vector.

Known open item, unchanged by this pass: this bridge executes the SAME
``opencode`` binary as ``OpenCodeBridge``, differing only by a ``--model`` flag.
Router-level provider identity is therefore a label, not an execution boundary
(F-M3.3-FB-9).
"""

from pathlib import Path

from .dispatch import WorkerDispatch


class DeepSeekBridge(WorkerDispatch):
    """Bridge adapter for DeepSeek / Freebuff adversarial reviewers."""

    handle_prefix = "deepseek"

    def __init__(self, runner: object | None = None, provider_model: str = "deepseek-coder") -> None:
        super().__init__(runner=runner)
        self._provider_model = provider_model

    def _argv(self, prompt: str, workdir: Path) -> list[str]:
        del workdir  # the model is selected via --model; cwd carries the workdir
        return ["opencode", "run", f"--model={self._provider_model}", prompt]


__all__ = ["DeepSeekBridge"]
