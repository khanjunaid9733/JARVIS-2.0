from __future__ import annotations

"""Autonomous Skill Runtime Engine and Goal Resolver (spec §20).

Bridges high-level goals and intents to deterministic skill executions,
closing the loop between discovery (SkillRegistry), health gating
(SkillHealthChecker), planner decomposition (SkillHTNBridge), and sandboxed
dispatching (SkillDispatcher).
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .context import SkillExecutionContext
from .dispatcher import SkillDispatcher, SkillExecutionResult
from .health import HealthStatus, SkillHealthChecker, SkillHealthReport
from .manifest import SkillManifest
from .registry import SkillMatch, SkillRegistry, get_default_registry


@dataclass(frozen=True)
class SkillGoalResult:
    """Outcome of resolving and executing a goal through the skill engine."""

    goal: str
    selected_skill: SkillManifest | None
    execution: SkillExecutionResult | None
    health: SkillHealthReport | None
    success: bool
    status: str  # "SUCCEEDED", "REFUSED", "NO_MATCH", "EXECUTION_FAILED"
    message: str = ""
    candidate_matches: tuple[str, ...] = ()
    duration_ms: float = 0.0


class SkillRuntimeEngine:
    """Autonomous goal resolver and execution engine for JARVIS skills."""

    def __init__(
        self,
        registry: SkillRegistry | None = None,
        dispatcher: SkillDispatcher | None = None,
        health_checker: SkillHealthChecker | None = None,
        event_sink: Any | None = None,
    ) -> None:
        self.registry = registry or get_default_registry()
        self.health_checker = health_checker or SkillHealthChecker()
        self.dispatcher = dispatcher or SkillDispatcher(
            health_checker=self.health_checker,
            event_sink=event_sink,
        )

    def resolve_skill(
        self,
        goal: str,
        domain: str | None = None,
        min_score: float = 0.5,
    ) -> tuple[SkillManifest | None, list[SkillMatch]]:
        """Find the most relevant executable skill for a given goal intent."""
        # 1. Exact match check
        normalized_id = goal.strip().lower().replace(" ", "-")
        exact = self.registry.get(normalized_id)
        if exact is not None:
            return exact, [SkillMatch(skill=exact, score=100.0, matched_terms=(normalized_id,))]

        # 2. Inverted index search
        matches = self.registry.find(goal, domain=domain, min_score=min_score, limit=5)
        if not matches:
            return None, []

        return matches[0].skill, matches

    def execute_goal(
        self,
        goal: str,
        context: SkillExecutionContext,
        domain: str | None = None,
        min_score: float = 0.5,
    ) -> SkillGoalResult:
        """Resolve a goal to an optimal skill, enforce safety gates, and execute."""
        start_time = time.perf_counter()
        skill, matches = self.resolve_skill(goal, domain=domain, min_score=min_score)

        candidate_ids = tuple(m.skill.id for m in matches)

        if skill is None:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return SkillGoalResult(
                goal=goal,
                selected_skill=None,
                execution=None,
                health=None,
                success=False,
                status="NO_MATCH",
                message=f"No matching skill found in registry for goal: {goal!r}",
                candidate_matches=candidate_ids,
                duration_ms=duration_ms,
            )

        # 1. Evaluate operational health
        health = self.health_checker.evaluate(skill)
        if not health.is_executable and not context.dry_run:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return SkillGoalResult(
                goal=goal,
                selected_skill=skill,
                execution=None,
                health=health,
                success=False,
                status="REFUSED",
                message=health.summary,
                candidate_matches=candidate_ids,
                duration_ms=duration_ms,
            )

        # 2. Dispatch execution under containment
        exec_res = self.dispatcher.dispatch(skill, context)
        duration_ms = (time.perf_counter() - start_time) * 1000

        if exec_res.is_refused:
            return SkillGoalResult(
                goal=goal,
                selected_skill=skill,
                execution=exec_res,
                health=health,
                success=False,
                status="REFUSED",
                message=exec_res.refusal_reason or "Execution refused",
                candidate_matches=candidate_ids,
                duration_ms=duration_ms,
            )

        if not exec_res.success:
            return SkillGoalResult(
                goal=goal,
                selected_skill=skill,
                execution=exec_res,
                health=health,
                success=False,
                status="EXECUTION_FAILED",
                message=exec_res.error or f"Skill failed with exit code {exec_res.exit_code}",
                candidate_matches=candidate_ids,
                duration_ms=duration_ms,
            )

        return SkillGoalResult(
            goal=goal,
            selected_skill=skill,
            execution=exec_res,
            health=health,
            success=True,
            status="SUCCEEDED",
            message=f"Successfully executed skill '{skill.id}' for goal: {goal!r}",
            candidate_matches=candidate_ids,
            duration_ms=duration_ms,
        )
