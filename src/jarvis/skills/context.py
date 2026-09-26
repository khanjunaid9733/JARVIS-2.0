from __future__ import annotations

"""Execution Context and Sandbox Boundary for Skill Invocation.

Enforces parameter binding, path jailing, timeout budgets, and isolation
parameters for safe execution of skills.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


@dataclass
class SkillExecutionContext:
    """Execution context and isolation boundaries for running a skill."""

    workspace: Path
    parameters: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    dry_run: bool = False
    allow_network: bool = True
    env_overrides: dict[str, str] = field(default_factory=dict)
    mission_id: str | None = None

    def __post_init__(self) -> None:
        self.workspace = Path(self.workspace).resolve()

    def is_path_jailed(self, target: Path | str) -> bool:
        """Check if target path resides within the workspace boundary."""
        try:
            resolved = Path(target).resolve()
            return resolved.is_relative_to(self.workspace)
        except Exception:
            return False

    def substitute_params(self, template: str) -> str:
        """Substitute {param_name} placeholders in template text."""
        result = template
        for k, v in self.parameters.items():
            placeholder = f"{{{k}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(v))
        return result
