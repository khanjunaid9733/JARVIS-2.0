from __future__ import annotations

"""Hierarchical Task Network (HTN) Planner Types (Milestone M5.1, spec §M5 / §80.5).

Defines preconditions, primitive operators, domain methods, HTN domains, and
planning failure exceptions.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence


class PlanningFailure(RuntimeError):
    """Base exception for planning failures."""


class RecursionLimitExceeded(PlanningFailure):
    """Raised when task decomposition exceeds recursion depth limit."""


class PreconditionFailed(PlanningFailure):
    """Raised when preconditions for a method fail."""


@dataclass(frozen=True)
class Precondition:
    """A deterministic predicate evaluated against current world state."""

    name: str
    predicate: Callable[[Mapping[str, Any]], bool]
    description: str = ""

    def evaluate(self, state: Mapping[str, Any]) -> bool:
        """Evaluate predicate safely without allowing exceptions to escape."""
        try:
            return bool(self.predicate(state))
        except Exception:
            return False


@dataclass(frozen=True)
class PrimitiveOperator:
    """An atomic executable action with declared locks and effects."""

    id: str
    summary: str
    action_type: str = "operator"
    contract_id: str = "operator.default"
    version: str = "1.0.0"
    required_locks: tuple[str, ...] = ()
    write_locks: tuple[str, ...] = ()
    expected_effects: tuple[str, ...] = ()
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DomainMethod:
    """A declared decomposition of a compound task into subtasks."""

    name: str
    task_name: str
    preconditions: tuple[Precondition, ...] = ()
    subtasks: tuple[str, ...] = ()


@dataclass(frozen=True)
class HTNDomain:
    """An immutable domain definition containing methods and primitive operators."""

    name: str
    methods: tuple[DomainMethod, ...] = ()
    operators: tuple[PrimitiveOperator, ...] = ()

    def get_methods_for_task(self, task_name: str) -> tuple[DomainMethod, ...]:
        """Return all methods matching task_name in strict declaration order."""
        return tuple(m for m in self.methods if m.task_name == task_name)

    def get_operator(self, operator_id: str) -> PrimitiveOperator | None:
        """Find a primitive operator by its identifier."""
        for op in self.operators:
            if op.id == operator_id:
                return op
        return None
