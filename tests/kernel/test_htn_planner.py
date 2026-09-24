from __future__ import annotations

"""Unit tests for Hierarchical Task Network (HTN) Planner (Milestone M5.1)."""

import pytest

from jarvis.kernel.manifest_dag import CompiledWorkOrder
from jarvis.kernel.planner import (
    DomainMethod,
    HTNDecomposer,
    HTNDomain,
    HTNPlanner,
    PlanningFailure,
    Precondition,
    PrimitiveOperator,
    RecursionLimitExceeded,
)
from jarvis.orchestrator.mission_runner import MissionStep


# ---------------------------------------------------------------------------
# Test Fixtures & Sample Domains
# ---------------------------------------------------------------------------

@pytest.fixture
def basic_domain() -> HTNDomain:
    op_plan = PrimitiveOperator(
        id="op_plan",
        summary="Draft the mission plan",
        required_locks=("lock/plan",),
    )
    op_execute = PrimitiveOperator(
        id="op_execute",
        summary="Execute primary mission payload",
        write_locks=("lock/workspace/",),
    )
    op_verify = PrimitiveOperator(
        id="op_verify",
        summary="Verify execution output independently",
        required_locks=("lock/workspace/",),
    )
    op_fallback_execute = PrimitiveOperator(
        id="op_fallback_execute",
        summary="Execute offline fallback mission payload",
        write_locks=("lock/workspace/",),
    )

    # Methods
    method_online = DomainMethod(
        name="execute_online",
        task_name="task_execute",
        preconditions=(
            Precondition(
                name="online_available",
                predicate=lambda state: state.get("online", False) is True,
                description="Requires network online status",
            ),
        ),
        subtasks=("op_execute",),
    )
    method_offline = DomainMethod(
        name="execute_offline",
        task_name="task_execute",
        preconditions=(
            Precondition(
                name="offline_permitted",
                predicate=lambda state: state.get("allow_offline", False) is True,
                description="Requires offline permission",
            ),
        ),
        subtasks=("op_fallback_execute",),
    )
    method_root = DomainMethod(
        name="mission_standard",
        task_name="mission_goal",
        preconditions=(),
        subtasks=("op_plan", "task_execute", "op_verify"),
    )

    return HTNDomain(
        name="sample_mission_domain",
        methods=(method_root, method_online, method_offline),
        operators=(op_plan, op_execute, op_verify, op_fallback_execute),
    )


# ---------------------------------------------------------------------------
# Planning Tests
# ---------------------------------------------------------------------------

def test_direct_primitive_operator_resolves(basic_domain):
    planner = HTNPlanner(basic_domain)
    plan = planner.plan("op_plan", world_state={})
    assert len(plan) == 1
    assert plan[0].id == "op_plan"


def test_multi_level_hierarchical_decomposition_online(basic_domain):
    planner = HTNPlanner(basic_domain)
    state = {"online": True, "allow_offline": True}
    plan = planner.plan("mission_goal", world_state=state)

    assert len(plan) == 3
    assert [op.id for op in plan] == ["op_plan", "op_execute", "op_verify"]


def test_precondition_backtracking_falls_back_to_offline(basic_domain):
    planner = HTNPlanner(basic_domain)
    # Online is False, but allow_offline is True -> should select method_offline
    state = {"online": False, "allow_offline": True}
    plan = planner.plan("mission_goal", world_state=state)

    assert len(plan) == 3
    assert [op.id for op in plan] == ["op_plan", "op_fallback_execute", "op_verify"]


def test_unmet_preconditions_raise_planning_failure(basic_domain):
    planner = HTNPlanner(basic_domain)
    # Neither online nor allow_offline is set -> task_execute cannot decompose
    state = {"online": False, "allow_offline": False}
    with pytest.raises(PlanningFailure, match="No valid HTN decomposition found"):
        planner.plan("mission_goal", world_state=state)


def test_unknown_task_raises_planning_failure(basic_domain):
    planner = HTNPlanner(basic_domain)
    with pytest.raises(PlanningFailure, match="No valid HTN decomposition found"):
        planner.plan("non_existent_task", world_state={})


def test_circular_task_graph_raises_recursion_limit():
    method_a = DomainMethod(name="method_a", task_name="task_a", subtasks=("task_b",))
    method_b = DomainMethod(name="method_b", task_name="task_b", subtasks=("task_a",))

    domain = HTNDomain(
        name="cyclic_domain",
        methods=(method_a, method_b),
        operators=(),
    )
    planner = HTNPlanner(domain)
    with pytest.raises(RecursionLimitExceeded, match="exceeded recursion depth limit"):
        planner.plan("task_a", world_state={}, max_depth=8)


def test_deterministic_method_ordering():
    op1 = PrimitiveOperator(id="op1", summary="Method 1 result")
    op2 = PrimitiveOperator(id="op2", summary="Method 2 result")
    m1 = DomainMethod(name="m1", task_name="goal", subtasks=("op1",))
    m2 = DomainMethod(name="m2", task_name="goal", subtasks=("op2",))

    # Domain with m1 declared first
    domain_m1_first = HTNDomain(name="d1", methods=(m1, m2), operators=(op1, op2))
    plan1 = HTNPlanner(domain_m1_first).plan("goal", {})
    assert plan1[0].id == "op1"

    # Domain with m2 declared first
    domain_m2_first = HTNDomain(name="d2", methods=(m2, m1), operators=(op1, op2))
    plan2 = HTNPlanner(domain_m2_first).plan("goal", {})
    assert plan2[0].id == "op2"


def test_world_state_immutability(basic_domain):
    planner = HTNPlanner(basic_domain)
    state = {"online": True, "allow_offline": True, "nested": {"counter": 1}}
    expected_state = {"online": True, "allow_offline": True, "nested": {"counter": 1}}

    planner.plan("mission_goal", world_state=state)
    assert state == expected_state


def test_failing_precondition_exception_handled_safely():
    def broken_predicate(state):
        return state["non_existent_key"]["deep_key"] == "boom"

    broken_precondition = Precondition(name="broken", predicate=broken_predicate)
    op = PrimitiveOperator(id="op", summary="Operator")
    method = DomainMethod(name="m", task_name="goal", preconditions=(broken_precondition,), subtasks=("op",))
    domain = HTNDomain(name="d", methods=(method,), operators=(op,))

    planner = HTNPlanner(domain)
    # The exception inside broken_predicate should be caught safely by Precondition.evaluate -> returns False
    with pytest.raises(PlanningFailure):
        planner.plan("goal", {})


# ---------------------------------------------------------------------------
# Decomposer Adapter & ManifestDAG Integration Tests
# ---------------------------------------------------------------------------

def test_htn_decomposer_emits_mission_steps(basic_domain):
    planner = HTNPlanner(basic_domain)
    decomposer = HTNDecomposer(
        planner=planner,
        state_provider=lambda: {"online": True},
        default_task="mission_goal",
    )

    steps = decomposer.decompose("any goal label")
    assert isinstance(steps, tuple)
    assert len(steps) == 3
    assert all(isinstance(s, MissionStep) for s in steps)
    assert steps[0].id == "op_plan"
    assert steps[1].id == "op_execute"
    assert steps[2].id == "op_verify"


def test_htn_decomposer_compiles_manifest_dag(basic_domain):
    planner = HTNPlanner(basic_domain)
    decomposer = HTNDecomposer(
        planner=planner,
        state_provider=lambda: {"online": True},
    )

    ops = decomposer.plan_operators("mission_goal")
    dag = decomposer.compile_dag(ops)

    assert isinstance(dag, CompiledWorkOrder)
    assert dag.total_effects == 3
    assert dag.total_stages >= 1
    # Check that execution stages exist and have digests
    assert dag.dag_digest != ""
    for stage in dag.stages:
        assert len(stage.effect_ids) > 0


def test_htn_decomposer_manifest_dag_detects_lock_conflicts():
    op_write1 = PrimitiveOperator(
        id="write_a",
        summary="Write file a",
        write_locks=("data/store/",),
    )
    op_write2 = PrimitiveOperator(
        id="write_b",
        summary="Write file b",
        write_locks=("data/store/sub/",),
    )
    domain = HTNDomain(name="lock_domain", operators=(op_write1, op_write2))
    planner = HTNPlanner(domain)
    decomposer = HTNDecomposer(planner=planner)

    # Sequential dependent writes on overlapping hierarchical locks
    dag = decomposer.compile_dag((op_write1, op_write2))
    assert dag.total_stages == 2  # Serialized into distinct stages
    assert dag.stages[0].effect_ids == ("write_a",)
    assert dag.stages[1].effect_ids == ("write_b",)
