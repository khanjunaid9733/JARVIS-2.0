from __future__ import annotations

"""Freebuff (DeepSeek) Adversarial Red-Team Probes — Milestone M2.7: Manifest DAG & Compilation.

Role: Adversarial Architecture & Research Reviewer (AGENTS.md §4.2).
Focus: Stress-testing, boundary breaking, race condition tracing, lock contention,
and dependency resolution loopholes in `src/jarvis/kernel/manifest_dag.py`.

Findings Catalog:
  - F-M2.7-FB-1 (MEDIUM): Resource locks lack URI / case canonicalization;
    case or scheme variations on identical resources allow concurrent write collisions.
  - F-M2.7-FB-2 (HIGH): `build_dag_from_manifest` only inspects shallow args;
    dependencies nested within sub-dictionaries are dropped, causing producer-consumer race conditions.
  - F-M2.7-FB-3 (LOW): Alphabetical tie-breaking in stage planning allows trivial tasks
    to preempt critical-path tasks with high downstream fan-out, causing stage inflation.
  - F-M2.7-FB-4 (INFORMATIONAL): Exact string matching on resource paths does not
    recognize directory/file hierarchy (e.g. locking `dir/` does not block `dir/file.txt`).
  - F-M2.7-FB-5 (MEDIUM): Whitespace-only effect IDs (`"   "`) are accepted,
    producing ambiguous DAG nodes and obscure cycle traces.
"""

import pytest

from jarvis.kernel.intent import Budget, Manifest, ResolvedContract
from jarvis.kernel.manifest_dag import (
    CompiledWorkOrder,
    EffectNode,
    ExecutionStage,
    ManifestCycleError,
    build_dag_from_manifest,
    compile_from_manifest,
    compile_manifest_dag,
    plan_execution_stages,
    validate_acyclic,
)


# ---------------------------------------------------------------------------
# F-M2.7-FB-1: Resource Lock Normalization & Case Collisions
# ---------------------------------------------------------------------------

def test_fb_m2_7_1_case_variant_lock_collision_not_prevented():
    """F-M2.7-FB-1: Resource locks use raw string equality. Two effects declaring
    write locks with case variations (e.g. 'FILE://foo' vs 'file://foo') are not
    recognized as conflicting, allowing concurrent execution in Stage 0.

    Adversarial vulnerability: On case-insensitive filesystems (Windows/macOS),
    this results in unisolated concurrent writes to the identical file.
    """
    node1 = EffectNode(id="w1", contract_id="write", write_locks=("file://Workspace/file.txt",))
    node2 = EffectNode(id="w2", contract_id="write", write_locks=("FILE://workspace/file.txt",))

    stages = plan_execution_stages([node1, node2])

    # Currently: raw string comparison considers these distinct resources!
    # They both end up in stage 0 concurrently.
    assert len(stages) == 1, "Raw string equality allowed concurrent writes to case-variant URI"
    assert set(stages[0].effect_ids) == {"w1", "w2"}
    # Recommendation: Introduce resource_key canonicalization (e.g., lowercase scheme & path).


# ---------------------------------------------------------------------------
# F-M2.7-FB-2: Nested Dictionary Args Dependency Dropping
# ---------------------------------------------------------------------------

def test_fb_m2_7_2_nested_dict_args_dependency_dropped():
    """F-M2.7-FB-2: `build_dag_from_manifest` only inspects top-level values and
    1-level list items of `args`. Contract references nested inside sub-dictionaries
    (e.g. `{'config': {'input_contract': 'producer'}}`) are completely missed.

    Adversarial vulnerability: Producer-consumer data dependencies are dropped,
    causing the consumer to execute in parallel with or before the producer!
    """
    manifest = Manifest(
        manifest_id="mf-nested",
        intent_id="int-nested",
        contracts=[
            ResolvedContract(
                id="producer",
                version="1.0.0",
                args={"output_file": "data.json"},
            ),
            ResolvedContract(
                id="consumer",
                version="1.0.0",
                args={
                    "pipeline_config": {
                        "source_contract": "producer",  # NESTED contract reference!
                    }
                },
            ),
        ],
        required_capabilities=["c1", "c2"],
        budget=Budget(),
        constraints={},
        risk_class="safe",
        manifest_sha256="dummy",
        created_at_utc="2026-09-21T00:00:00Z",
    )

    nodes = build_dag_from_manifest(manifest)
    consumer_node = next(n for n in nodes if n.id == "consumer")

    # Characterization: Consumer failed to capture the dependency because it's nested in a dict
    assert "producer" not in consumer_node.depends_on, (
        "Nested dict dependency was unexpectedly captured"
    )

    # Consequently, both are scheduled in Stage 0 in parallel!
    order = compile_from_manifest(manifest)
    assert order.concurrency_plan["producer"] == 0
    assert order.concurrency_plan["consumer"] == 0  # RACE CONDITION: Consumer runs before/with producer!


# ---------------------------------------------------------------------------
# F-M2.7-FB-3: Critical Path Inversion via Alphabetical Sorting
# ---------------------------------------------------------------------------

def test_fb_m2_7_3_critical_path_preemption_by_alphabetical_sorting():
    """F-M2.7-FB-3: Tie-breaking is strictly alphabetical by effect ID.
    If a low-priority effect ('a_trivial') and a critical-path root effect ('z_critical')
    conflict on a resource lock, 'a_trivial' is greedily scheduled first,
    pushing the entire deep dependency tree behind 'z_critical' by an entire stage.
    """
    # z_critical unblocks a deep chain: z_critical -> z_step2 -> z_step3
    # a_trivial has NO downstream dependents
    nodes = [
        EffectNode(id="a_trivial", contract_id="c1", write_locks=("res://shared",)),
        EffectNode(id="z_critical", contract_id="c2", write_locks=("res://shared",)),
        EffectNode(id="z_step2", contract_id="c3", depends_on=("z_critical",)),
        EffectNode(id="z_step3", contract_id="c4", depends_on=("z_step2",)),
    ]

    stages = plan_execution_stages(nodes)

    # a_trivial gets stage 0 purely because 'a' < 'z'
    assert stages[0].effect_ids == ("a_trivial",)
    assert stages[1].effect_ids == ("z_critical",)
    assert stages[2].effect_ids == ("z_step2",)
    assert stages[3].effect_ids == ("z_step3",)
    # Total stages = 4. If z_critical ran first: Stage 0: [z_critical], Stage 1: [a_trivial, z_step2], Stage 2: [z_step3] -> Total stages = 3!
    assert len(stages) == 4, "Alphabetical tie-breaking resulted in pipeline stage inflation"


# ---------------------------------------------------------------------------
# F-M2.7-FB-4: Hierarchical Resource Escape
# ---------------------------------------------------------------------------

def test_fb_m2_7_4_hierarchical_resource_escape():
    """F-M2.7-FB-4: Exact string matching does not recognize resource containment.
    An exclusive write lock on a directory 'dir/' does not conflict with a read
    or write lock on 'dir/subfile.txt'.
    """
    node_dir = EffectNode(id="n_dir", contract_id="write", write_locks=("dir/",))
    node_file = EffectNode(id="n_file", contract_id="read", read_locks=("dir/subfile.txt",))

    stages = plan_execution_stages([node_dir, node_file])

    # Characterization: Both scheduled concurrently in stage 0
    assert len(stages) == 1
    assert set(stages[0].effect_ids) == {"n_dir", "n_file"}


# ---------------------------------------------------------------------------
# F-M2.7-FB-5: Whitespace-Only Effect IDs
# ---------------------------------------------------------------------------

def test_fb_m2_7_5_whitespace_only_effect_ids():
    """F-M2.7-FB-5: Pydantic EffectNode permits whitespace-only IDs ('   '),
    which can lead to confusing cycle reports and difficult debugging.
    """
    node = EffectNode(id="   ", contract_id="test")
    assert node.id == "   "
    # validate_acyclic permits it as a valid node ID
    deps = validate_acyclic([node])
    assert "   " in deps


# ---------------------------------------------------------------------------
# Characterization: Disjoint Graph Multi-Cycle Isolation
# ---------------------------------------------------------------------------

def test_fb_m2_7_6_disjoint_graph_deterministic_first_cycle_reporting():
    """Characterization: When two disjoint subgraphs both contain cycles,
    DFS deterministically halts and reports the cycle with the lowest root key.
    """
    # Graph 1: X -> Y -> X
    # Graph 2: A -> B -> A
    nodes = [
        EffectNode(id="X", contract_id="t", depends_on=("Y",)),
        EffectNode(id="Y", contract_id="t", depends_on=("X",)),
        EffectNode(id="A", contract_id="t", depends_on=("B",)),
        EffectNode(id="B", contract_id="t", depends_on=("A",)),
    ]

    with pytest.raises(ManifestCycleError) as exc_info:
        validate_acyclic(nodes)

    # Because roots are visited alphabetically ('A' before 'X'), cycle in A/B is reported first
    assert "A" in exc_info.value.cycle
    assert "B" in exc_info.value.cycle
    assert "X" not in exc_info.value.cycle
