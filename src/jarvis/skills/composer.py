from __future__ import annotations

"""Skill Pipeline Composer and Chaining Engine.

Enables composing multiple individual skills into deterministic, ordered
execution pipelines with parameter propagation and fail-closed error boundaries.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .context import SkillExecutionContext
from .dispatcher import SkillDispatcher, SkillExecutionResult
from .manifest import SkillManifest
from .registry import SkillRegistry


@dataclass(frozen=True)
class PipelineStep:
    """A single stage in a multi-skill pipeline."""

    step_id: str
    skill_id: str
    input_mapping: Mapping[str, str] = field(default_factory=dict)
    # Optional condition predicate: if false, skip step
    condition_key: str | None = None


@dataclass(frozen=True)
class PipelineResult:
    """Consolidated outcome of a skill pipeline execution."""

    pipeline_name: str
    success: bool
    completed_steps: int
    total_steps: int
    step_results: tuple[SkillExecutionResult, ...]
    final_output: str = ""
    error: str | None = None


class SkillPipelineComposer:
    """Executes ordered multi-skill workflows."""

    def __init__(
        self,
        registry: SkillRegistry,
        dispatcher: SkillDispatcher,
    ) -> None:
        self.registry = registry
        self.dispatcher = dispatcher

    def execute_pipeline(
        self,
        name: str,
        steps: Sequence[PipelineStep],
        initial_params: Mapping[str, Any],
        workspace: Path,
        dry_run: bool = False,
    ) -> PipelineResult:
        """Run each step sequentially, propagating parameters across steps."""
        current_params = dict(initial_params)
        results: list[SkillExecutionResult] = []

        for step in steps:
            skill = self.registry.get(step.skill_id)
            if not skill:
                return PipelineResult(
                    pipeline_name=name,
                    success=False,
                    completed_steps=len(results),
                    total_steps=len(steps),
                    step_results=tuple(results),
                    error=f"Step '{step.step_id}' references unknown skill '{step.skill_id}'.",
                )

            # Map inputs for this step
            step_params = dict(current_params)
            for target_key, src_key in step.input_mapping.items():
                if src_key in current_params:
                    step_params[target_key] = current_params[src_key]

            ctx = SkillExecutionContext(
                workspace=workspace,
                parameters=step_params,
                dry_run=dry_run,
            )

            res = self.dispatcher.dispatch(skill, ctx)
            results.append(res)

            if not res.success:
                return PipelineResult(
                    pipeline_name=name,
                    success=False,
                    completed_steps=len(results) - 1,
                    total_steps=len(steps),
                    step_results=tuple(results),
                    error=f"Pipeline halted at step '{step.step_id}' ({skill.id}): {res.error or res.refusal_reason}",
                )

            # Capture raw stdout into current_params as last_output
            clean_output = res.raw_output if res.raw_output else res.stdout.strip()
            current_params["last_output"] = clean_output
            current_params[f"{step.step_id}_output"] = clean_output

        last_text = results[-1].stdout if results else ""
        return PipelineResult(
            pipeline_name=name,
            success=True,
            completed_steps=len(results),
            total_steps=len(steps),
            step_results=tuple(results),
            final_output=last_text,
        )
