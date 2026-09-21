from __future__ import annotations

"""Freebuff (DeepSeek) Adversarial Red-Team Probes — Milestone M2.7: Manifest DAG & Compilation.

Role: Adversarial Architecture & Research Reviewer (AGENTS.md §4.2).

DISPOSITION — updated at fix time. Four of the original six probes pinned the
DEFECTIVE behaviour (they asserted the bug exists). Such a pin cannot survive the
fix and must be removed with the bug, never edited to keep passing. Those four are
retired here; their requirements are now asserted green, as invariants, by
`tests/review/test_freebuff_invariants_m2_7.py`:

  CLOSED -> invariant probe
  - F-M2.7-FB-1 lock canonicalisation   -> test_invariant_scheme_case_variants_of_one_resource_are_exclusive
                                           test_invariant_path_case_variants_of_one_path_are_exclusive
  - F-M2.7-FB-2 nested args dependency  -> test_invariant_nested_args_contract_reference_creates_dependency
  - F-M2.7-FB-4 hierarchical lock keys  -> test_invariant_directory_lock_conflicts_with_descendant
  - F-M2.7-FB-5 effect id normalisation -> test_invariant_blank_effect_id_is_rejected

  RETAINED here
  - F-M2.7-FB-3 (LOW): alphabetical tie-breaking can inflate the wave count versus
    critical-path-first ordering. Still OPEN. It is a design change against a
    declared determinism invariant (module docstring Invariant 4), not a defect,
    so no invariant probe covers it — it needs a creator ruling, not a test.
  - F-M2.7-FB-6 (characterisation): deterministic first-cycle reporting.

FIX CONSTRAINT still live for F-M2.7-FB-2: dependency inference remains string
equality against contract ids, so an incidental argument that happens to spell a
sibling contract's id still creates an edge. Recursion widened the reach of that
heuristic rather than removing it. Requiring a declared reference (`depends_on`, or
a named key) is a design change; it is recorded as a PROPOSAL in the invariant file.
"""

import pytest

from jarvis.kernel.manifest_dag import (
    EffectNode,
    ManifestCycleError,
    plan_execution_stages,
    validate_acyclic,
)


# ---------------------------------------------------------------------------
# F-M2.7-FB-3: Critical Path Inversion via Alphabetical Sorting (OPEN — proposal)
# ---------------------------------------------------------------------------

def test_fb_m2_7_3_critical_path_preemption_by_alphabetical_sorting():
    """F-M2.7-FB-3: Tie-breaking is strictly alphabetical by effect ID.
    If a low-priority effect ('a_trivial') and a critical-path root effect ('z_critical')
    conflict on a resource lock, 'a_trivial' is greedily scheduled first,
    pushing the entire deep dependency tree behind 'z_critical' by an entire stage.

    Retained as an OPEN finding: greedy packing is not optimal in general, so this
    does not become a defect until critical-path-first ordering is ruled in as the
    tie-break policy.
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
