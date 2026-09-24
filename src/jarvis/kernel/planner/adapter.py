from __future__ import annotations

"""HTN Decomposer Adapter (Milestone M5.1, spec §M5 / §80.5).

Bridges HTNPlanner with the MissionRunner Decomposer protocol and compiles
planned operators into validated ManifestDAG execution structures.
"""

from typing import Any, Callable, Mapping, Sequence

from jarvis.kernel.manifest_dag import CompiledWorkOrder, EffectNode, compile_manifest_dag
from jarvis.orchestrator.mission_runner import MissionStep

from .htn import HTNPlanner
from .types import PrimitiveOperator


class HTNDecomposer:
    """Adapts HTNPlanner to the Decomposer protocol expected by MissionRunner and LiveRuntime."""

    def __init__(
        self,
        planner: HTNPlanner,
        state_provider: Callable[[], Mapping[str, Any]] | None = None,
        default_task: str | None = None,
    ) -> None:
        self.planner = planner
        self.state_provider = state_provider or (lambda: {})
        self.default_task = default_task

    def plan_operators(self, goal: str) -> tuple[PrimitiveOperator, ...]:
        """Decompose a goal string into resolved primitive operators."""
        world_state = self.state_provider()
        task_name = self.default_task or goal
        ops = self.planner.plan(task_name, world_state)
        return tuple(ops)

    def decompose(self, goal: str) -> tuple[MissionStep, ...]:
        """Fulfill Decomposer protocol: return ordered tuple of MissionSteps."""
        ops = self.plan_operators(goal)
        return tuple(MissionStep(id=op.id, summary=op.summary) for op in ops)

    def to_manifest_nodes(self, operators: Sequence[PrimitiveOperator]) -> tuple[EffectNode, ...]:
        """Convert planned operators into EffectNodes for ManifestDAG validation."""
        nodes: list[EffectNode] = []
        for i, op in enumerate(operators):
            # By default, a linear HTN plan establishes sequential dependencies
            depends_on = (operators[i - 1].id,) if i > 0 else ()
            nodes.append(
                EffectNode(
                    id=op.id,
                    contract_id=op.contract_id,
                    version=op.version,
                    depends_on=depends_on,
                    read_locks=op.required_locks,
                    write_locks=op.write_locks,
                    args=dict(op.parameters) if op.parameters else {},
                )
            )
        return tuple(nodes)

    def compile_dag(
        self, operators: Sequence[PrimitiveOperator], manifest_id: str = "htn_plan"
    ) -> CompiledWorkOrder:
        """Compile planned operators into an acyclic CompiledWorkOrder with parallel waves."""
        nodes = self.to_manifest_nodes(operators)
        return compile_manifest_dag(manifest_id, nodes)

