from __future__ import annotations

"""Skill Health and Precondition Verification Engine.

Performs deterministic, fail-closed verification of skill prerequisites
(system binaries, environment variables, Python modules, network)
prior to execution.
"""

import importlib.util
import os
import shutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from .manifest import SkillManifest


class HealthStatus(str, Enum):
    """Operational readiness status for a skill."""

    HEALTHY = "healthy"          # All prerequisites satisfied; ready for execution
    DEGRADED = "degraded"        # Non-critical prerequisite missing (e.g. optional env)
    UNAVAILABLE = "unavailable"  # Critical prerequisite missing; execution forbidden


@dataclass(frozen=True)
class SkillHealthReport:
    """Detailed health check evaluation for a skill."""

    skill_id: str
    status: HealthStatus
    is_executable: bool
    missing_binaries: tuple[str, ...] = ()
    missing_env_vars: tuple[str, ...] = ()
    missing_modules: tuple[str, ...] = ()
    missing_paths: tuple[str, ...] = ()
    remediation_notes: tuple[str, ...] = ()

    @property
    def summary(self) -> str:
        if self.status == HealthStatus.HEALTHY:
            return f"Skill '{self.skill_id}' is ready and fully healthy."
        items = []
        if self.missing_binaries:
            items.append(f"missing binaries: {', '.join(self.missing_binaries)}")
        if self.missing_env_vars:
            items.append(f"missing env: {', '.join(self.missing_env_vars)}")
        if self.missing_modules:
            items.append(f"missing python modules: {', '.join(self.missing_modules)}")
        return f"Skill '{self.skill_id}' [{self.status.value}]: {'; '.join(items)}"


class SkillHealthChecker:
    """Verifies skill operational prerequisites without side effects."""

    def __init__(self, env: dict[str, str] | None = None) -> None:
        self.env = env if env is not None else dict(os.environ)

    def check_binary(self, name: str) -> bool:
        """Check if an executable binary is present in system PATH."""
        return shutil.which(name) is not None

    def check_env_var(self, name: str) -> bool:
        """Check if an environment variable is non-empty."""
        return bool(self.env.get(name))

    def check_python_module(self, module_name: str) -> bool:
        """Check if a Python module is importable without importing it."""
        try:
            return importlib.util.find_spec(module_name) is not None
        except Exception:
            return False

    def evaluate(self, skill: SkillManifest) -> SkillHealthReport:
        """Evaluate the full prerequisite health for a SkillManifest."""
        missing_binaries: list[str] = []
        missing_env_vars: list[str] = []
        missing_modules: list[str] = []
        notes: list[str] = []

        # 1. Check declared or inferred binaries
        for binary in skill.prerequisites.required_binaries:
            if not self.check_binary(binary):
                missing_binaries.append(binary)
                notes.append(f"Install '{binary}' or ensure it is accessible on system PATH.")

        # 2. Check declared environment variables
        for env_var in skill.prerequisites.required_env_vars:
            if not self.check_env_var(env_var):
                missing_env_vars.append(env_var)
                notes.append(f"Set environment variable '{env_var}'.")

        # 3. Check declared Python modules
        for mod in skill.prerequisites.required_python_modules:
            if not self.check_python_module(mod):
                missing_modules.append(mod)
                notes.append(f"Install Python module '{mod}' via pip/uv.")

        # Determine status
        if not missing_binaries and not missing_env_vars and not missing_modules:
            status = HealthStatus.HEALTHY
            is_executable = True
        elif missing_binaries or missing_modules:
            status = HealthStatus.UNAVAILABLE
            is_executable = False
        else:
            # Only missing env vars: degraded (might fail at auth time)
            status = HealthStatus.DEGRADED
            is_executable = False

        return SkillHealthReport(
            skill_id=skill.id,
            status=status,
            is_executable=is_executable,
            missing_binaries=tuple(missing_binaries),
            missing_env_vars=tuple(missing_env_vars),
            missing_modules=tuple(missing_modules),
            remediation_notes=tuple(notes),
        )

    def evaluate_batch(self, skills: Sequence[SkillManifest]) -> dict[str, SkillHealthReport]:
        """Evaluate health across a collection of skills."""
        return {s.id: self.evaluate(s) for s in skills}
