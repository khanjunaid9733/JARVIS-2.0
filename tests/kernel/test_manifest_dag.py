from __future__ import annotations

"""Unit & Invariant Tests for Milestone M2.7: Manifest Compilation & DAG Validation."""

import pytest

from jarvis.kernel.intent import Budget, Manifest, ResolvedContract
from jarvis.kernel.manifest_dag import (
    CompiledWorkOrder,
    ConflictingLockDeclarationError,
    DanglingDependencyError,
    EffectNode,
    ExecutionStage,
    LockMode,
    ManifestCycleError,
    ResourceLock,
    build_dag_from_manifest,
    compile_from_manifest,
    compile_manifest_dag,
    plan_execution_stages,
    validate_acyclic,
)


# ---------------------------------------------------------------------------
# 1. Acyclic Dependency Validation & Cycle Detection
# ---------------------------------------------------------------------------

def test_validate_acyclic_empty_and_single():
    """Empty nodes and single node validate cleanly."""
    assert validate_acyclic([]) == {}

    node = EffectNode(id="e1", contract_id="fs.read")
    deps = validate_acyclic([node])
    assert deps == {"e1": set()}


def test_validate_acyclic_linear_and_diamond():
    """Valid DAGs (linear chain and diamond) pass validation."""
    # Linear: e1 -> e2 -> e3 (e3 depends on e2, e2 depends on e1)
    nodes_linear = [
        EffectNode(id="e1", contract_id="fs.read"),
        EffectNode(id="e2", contract_id="fs.write", depends_on=("e1",)),
        EffectNode(id="e3", contract_id="fs.read", depends_on=("e2",)),
    ]
    deps = validate_acyclic(nodes_linear)
    assert deps["e1"] == set()
    assert deps["e2"] == {"e1"}
    assert deps["e3"] == {"e2"}

    # Diamond: e1 -> e2, e1 -> e3, e2 & e3 -> e4
    nodes_diamond = [
        EffectNode(id="e1", contract_id="start"),
        EffectNode(id="e2", contract_id="branch_a", depends_on=("e1",)),
        EffectNode(id="e3", contract_id="branch_b", depends_on=("e1",)),
        EffectNode(id="e4", contract_id="join", depends_on=("e2", "e3")),
    ]
    deps_d = validate_acyclic(nodes_diamond)
    assert deps_d["e1"] == set()
    assert deps_d["e2"] == {"e1"}
    assert deps_d["e3"] == {"e1"}
    assert deps_d["e4"] == {"e2", "e3"}


def test_validate_acyclic_detects_self_cycle():
    """Direct self-dependency (A -> A) raises ManifestCycleError."""
    node = EffectNode(id="e1", contract_id="fs.read", depends_on=("e1",))
    with pytest.raises(ManifestCycleError) as exc_info:
        validate_acyclic([node])

    assert exc_info.value.cycle == ["e1", "e1"]
    assert "Dependency cycle detected" in str(exc_info.value)


def test_validate_acyclic_detects_two_node_cycle():
    """Mutual dependency (A -> B -> A) raises ManifestCycleError."""
    nodes = [
        EffectNode(id="A", contract_id="test", depends_on=("B",)),
        EffectNode(id="B", contract_id="test", depends_on=("A",)),
    ]
    with pytest.raises(ManifestCycleError) as exc_info:
        validate_acyclic(nodes)

    assert "A" in exc_info.value.cycle
    assert "B" in exc_info.value.cycle


def test_validate_acyclic_detects_three_node_cycle():
    """Multi-node indirect cycle (A -> B -> C -> A) raises ManifestCycleError."""
    nodes = [
        EffectNode(id="A", contract_id="test", depends_on=("B",)),
        EffectNode(id="B", contract_id="test", depends_on=("C",)),
        EffectNode(id="C", contract_id="test", depends_on=("A",)),
    ]
    with pytest.raises(ManifestCycleError) as exc_info:
        validate_acyclic(nodes)

    assert len(exc_info.value.cycle) >= 3


def test_validate_acyclic_dangling_dependency():
    """Dependency on non-existent effect ID raises DanglingDependencyError."""
    nodes = [
        EffectNode(id="A", contract_id="test", depends_on=("NON_EXISTENT",)),
    ]
    with pytest.raises(DanglingDependencyError) as exc_info:
        validate_acyclic(nodes)

    assert exc_info.value.effect_id == "A"
    assert exc_info.value.missing_id == "NON_EXISTENT"


def test_validate_acyclic_duplicate_id():
    """Duplicate effect IDs in manifest raise ValueError."""
    nodes = [
        EffectNode(id="A", contract_id="c1"),
        EffectNode(id="A", contract_id="c2"),
    ]
    with pytest.raises(ValueError, match="Duplicate effect ID 'A'"):
        validate_acyclic(nodes)


def test_validate_acyclic_conflicting_internal_locks():
    """Effect declaring both read and write locks on the same resource raises ConflictingLockDeclarationError."""
    node = EffectNode(
        id="A",
        contract_id="c1",
        read_locks=("file://same",),
        write_locks=("file://same",),
    )
    with pytest.raises(ConflictingLockDeclarationError) as exc_info:
        validate_acyclic([node])

    assert exc_info.value.effect_id == "A"
    assert exc_info.value.resource == "file://same"


# ---------------------------------------------------------------------------
# 2. Execution Wave Planner (Parallel vs. Serial Scheduling)
# ---------------------------------------------------------------------------

def test_plan_execution_empty():
    assert plan_execution_stages([]) == ()


def test_plan_execution_fully_parallel():
    """Independent effects without resource conflicts run in a single parallel stage."""
    nodes = [
        EffectNode(id="e1", contract_id="c1"),
        EffectNode(id="e2", contract_id="c2"),
        EffectNode(id="e3", contract_id="c3"),
    ]
    stages = plan_execution_stages(nodes)
    assert len(stages) == 1
    assert stages[0].stage_index == 0
    assert stages[0].effect_ids == ("e1", "e2", "e3")


def test_plan_execution_pure_serial_dependency():
    """Strict linear dependency chain produces one stage per effect."""
    nodes = [
        EffectNode(id="e1", contract_id="c1"),
        EffectNode(id="e2", contract_id="c2", depends_on=("e1",)),
        EffectNode(id="e3", contract_id="c3", depends_on=("e2",)),
    ]
    stages = plan_execution_stages(nodes)
    assert len(stages) == 3
    assert stages[0].effect_ids == ("e1",)
    assert stages[1].effect_ids == ("e2",)
    assert stages[2].effect_ids == ("e3",)


def test_plan_execution_diamond():
    """Diamond DAG produces [A], [B, C], [D]."""
    nodes = [
        EffectNode(id="A", contract_id="start"),
        EffectNode(id="B", contract_id="left", depends_on=("A",)),
        EffectNode(id="C", contract_id="right", depends_on=("A",)),
        EffectNode(id="D", contract_id="join", depends_on=("B", "C")),
    ]
    stages = plan_execution_stages(nodes)
    assert len(stages) == 3
    assert stages[0].effect_ids == ("A",)
    assert stages[1].effect_ids == ("B", "C")
    assert stages[2].effect_ids == ("D",)


def test_plan_execution_resource_locks_shared_reads():
    """Multiple effects holding shared read locks on the same resource run in parallel."""
    nodes = [
        EffectNode(id="r1", contract_id="read", read_locks=("res://shared",)),
        EffectNode(id="r2", contract_id="read", read_locks=("res://shared",)),
        EffectNode(id="r3", contract_id="read", read_locks=("res://shared",)),
    ]
    stages = plan_execution_stages(nodes)
    assert len(stages) == 1
    assert stages[0].effect_ids == ("r1", "r2", "r3")
    assert stages[0].read_locks == ("res://shared",)
    assert stages[0].write_locks == ()


def test_plan_execution_resource_locks_write_write_conflict():
    """Effects with conflicting exclusive write locks are serialized into separate stages."""
    nodes = [
        EffectNode(id="w1", contract_id="write", write_locks=("file://target",)),
        EffectNode(id="w2", contract_id="write", write_locks=("file://target",)),
    ]
    stages = plan_execution_stages(nodes)
    assert len(stages) == 2
    assert stages[0].effect_ids == ("w1",)
    assert stages[0].write_locks == ("file://target",)
    assert stages[1].effect_ids == ("w2",)
    assert stages[1].write_locks == ("file://target",)


def test_plan_execution_resource_locks_read_write_conflict():
    """An effect with a read lock and an effect with a write lock on the same resource cannot co-occur."""
    nodes = [
        EffectNode(id="reader", contract_id="read", read_locks=("db://table",)),
        EffectNode(id="writer", contract_id="write", write_locks=("db://table",)),
    ]
    stages = plan_execution_stages(nodes)
    assert len(stages) == 2
    # Alphabetical tie-breaker schedules reader first, then writer
    assert stages[0].effect_ids == ("reader",)
    assert stages[1].effect_ids == ("writer",)


def test_plan_execution_complex_mixed():
    """Mixed DAG with dependencies and lock conflicts:
    - A: independent, read_locks=("res1",)
    - B: independent, read_locks=("res1",)
    - C: independent, write_locks=("res1",) -> conflicts with A & B
    - D: depends on A, independent
    """
    nodes = [
        EffectNode(id="A", contract_id="read_a", read_locks=("res1",)),
        EffectNode(id="B", contract_id="read_b", read_locks=("res1",)),
        EffectNode(id="C", contract_id="write_c", write_locks=("res1",)),
        EffectNode(id="D", contract_id="dep_d", depends_on=("A",)),
    ]
    stages = plan_execution_stages(nodes)
    # Stage 0: A and B both read res1 (no conflict). C cannot run because it writes res1. D cannot run because A not completed.
    assert stages[0].effect_ids == ("A", "B")
    # Stage 1: C (write res1) and D (depends on A, completed) -> can they co-occur? D has no locks, C has write res1. Yes!
    assert stages[1].effect_ids == ("C", "D")
    assert len(stages) == 2


# ---------------------------------------------------------------------------
# 3. CompiledWorkOrder Compilation & Digest Stability
# ---------------------------------------------------------------------------

def test_compile_manifest_dag_properties():
    nodes = [
        EffectNode(id="s1", contract_id="c1"),
        EffectNode(id="s2", contract_id="c2", depends_on=("s1",)),
    ]
    order = compile_manifest_dag("manifest-123", nodes)

    assert order.manifest_id == "manifest-123"
    assert order.total_stages == 2
    assert order.total_effects == 2
    assert order.concurrency_plan == {"s1": 0, "s2": 1}
    assert order.dependency_graph == {"s1": [], "s2": ["s1"]}
    assert order.is_pure_serial is True
    assert order.is_fully_parallel is False
    assert order.max_concurrency == 1
    assert len(order.dag_digest) == 64


def test_compile_manifest_dag_determinism():
    """Input nodes in different orders yield identical CompiledWorkOrder and dag_digest."""
    node_a = EffectNode(id="A", contract_id="ca")
    node_b = EffectNode(id="B", contract_id="cb")
    node_c = EffectNode(id="C", contract_id="cc", depends_on=("A", "B"))

    order1 = compile_manifest_dag("man-1", [node_a, node_b, node_c])
    order2 = compile_manifest_dag("man-1", [node_c, node_b, node_a])
    order3 = compile_manifest_dag("man-1", [node_b, node_a, node_c])

    assert order1 == order2 == order3
    assert order1.dag_digest == order2.dag_digest == order3.dag_digest


# ---------------------------------------------------------------------------
# 4. Manifest Adapter (Intent Manifest Integration)
# ---------------------------------------------------------------------------

def test_build_dag_and_compile_from_manifest():
    """Demonstrates compilation directly from an existing jarvis.kernel.intent.Manifest."""
    manifest = Manifest(
        manifest_id="mf-999",
        intent_id="int-111",
        contracts=[
            ResolvedContract(
                id="c1",
                version="1.0.0",
                args={"target": "foo.txt", "write_locks": ["file://foo.txt"]},
            ),
            ResolvedContract(
                id="c2",
                version="1.0.0",
                args={
                    "source": "c1",  # data dependency on c1
                    "read_locks": ["file://foo.txt"],
                },
            ),
        ],
        required_capabilities=["fs.write", "fs.read"],
        budget=Budget(),
        constraints={},
        risk_class="safe",
        manifest_sha256="dummy-sha",
        created_at_utc="2026-09-21T00:00:00Z",
    )

    nodes = build_dag_from_manifest(manifest)
    assert len(nodes) == 2
    assert nodes[0].id == "c1"
    assert nodes[0].write_locks == ("file://foo.txt",)
    assert nodes[1].id == "c2"
    assert nodes[1].depends_on == ("c1",)  # extracted from args referencing "c1"
    assert nodes[1].read_locks == ("file://foo.txt",)

    work_order = compile_from_manifest(manifest)
    assert isinstance(work_order, CompiledWorkOrder)
    assert work_order.manifest_id == "mf-999"
    assert work_order.total_stages == 2
    assert work_order.concurrency_plan["c1"] == 0
    assert work_order.concurrency_plan["c2"] == 1
