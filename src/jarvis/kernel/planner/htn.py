from __future__ import annotations

"""Hierarchical Task Network (HTN) Planner (Milestone M5.1, spec §M5 / §80.5).

Provides deterministic total-order HTN decomposition with bounded backtracking,
state precondition evaluation, and fail-closed recursion limits.
"""

from typing import Any, Mapping, Sequence

from .types import (
    DomainMethod,
    HTNDomain,
    PlanningFailure,
    PrimitiveOperator,
    RecursionLimitExceeded,
)


class HTNPlanner:
    """Deterministic HTN decomposition engine."""

    def __init__(self, domain: HTNDomain) -> None:
        self.domain = domain

    def plan(
        self,
        goal_task: str,
        world_state: Mapping[str, Any],
        max_depth: int = 16,
    ) -> Sequence[PrimitiveOperator]:
        """Decompose a goal task into a sequence of primitive operators.

        Args:
            goal_task: Name of compound task or ID of primitive operator.
            world_state: Read-only mapping of world facts for precondition checks.
            max_depth: Maximum decomposition depth before raising RecursionLimitExceeded.

        Returns:
            Ordered tuple of PrimitiveOperators to execute.

        Raises:
            RecursionLimitExceeded: When decomposition exceeds max_depth.
            PlanningFailure: When no valid decomposition satisfies all preconditions.
        """
        result = self._decompose((goal_task,), world_state, depth=0, max_depth=max_depth)
        if result is None:
            raise PlanningFailure(f"No valid HTN decomposition found for goal {goal_task!r}")
        return result

    def _decompose(
        self,
        agenda: tuple[str, ...],
        world_state: Mapping[str, Any],
        depth: int,
        max_depth: int,
    ) -> tuple[PrimitiveOperator, ...] | None:
        """Internal recursive backtracking decomposition."""
        if not agenda:
            return ()

        if depth > max_depth:
            raise RecursionLimitExceeded(
                f"HTN planning exceeded recursion depth limit {max_depth} on task {agenda[0]!r}"
            )

        task_id = agenda[0]
        rest = agenda[1:]

        # 1. Check if task_id is a primitive operator
        op = self.domain.get_operator(task_id)
        if op is not None:
            tail_plan = self._decompose(rest, world_state, depth, max_depth)
            if tail_plan is not None:
                return (op,) + tail_plan
            return None

        # 2. Compound task: retrieve candidate methods in declaration order
        methods = self.domain.get_methods_for_task(task_id)
        if not methods:
            return None

        for method in methods:
            # Evaluate all declared preconditions against world_state
            if not self._check_preconditions(method, world_state):
                continue

            new_agenda = method.subtasks + rest
            sub_plan = self._decompose(new_agenda, world_state, depth + 1, max_depth)
            if sub_plan is not None:
                return sub_plan

        return None

    @staticmethod
    def _check_preconditions(method: DomainMethod, world_state: Mapping[str, Any]) -> bool:
        """Evaluate all method preconditions without modifying world_state."""
        for p in method.preconditions:
            if not p.evaluate(world_state):
                return False
        return True
