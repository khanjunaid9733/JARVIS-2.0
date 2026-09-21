from __future__ import annotations

"""Freebuff (DeepSeek) INVARIANT probes — Milestone M2.7: Manifest compilation & DAG validation.

Role: Adversarial Architecture & Research Reviewer (AGENTS.md §4.2).
Convention (mirrors `test_freebuff_redteam_m3_3.py`):

  * `test_invariant_*` — states what the module's OWN declared contract requires and
    is **RED** today. Each one names a finding and fails until the defect is closed.
    These are the change-ready target: fixing the finding flips them green.
  * `test_current_*` — characterises today's behaviour and is **GREEN**. These pin
    the boundaries the fix must respect (they must STILL pass after the fix).

Companion file `test_freebuff_redteam_m2_7.py` (committed at 0f57bf5) held GREEN
pins of the same defects. Closing a finding necessarily flips the matching pin red,
and such a pin is retired with the bug rather than edited to keep passing: the four
satisfied pins (FB-1/2/4/5) were retired in the same change that closed them, and
that file now retains only FB-3 (open design proposal) and FB-6 (characterisation).

Findings covered:
  - F-M2.7-FB-1: resource locks are compared by raw string equality; no canonical
    resource key is derived.
  - F-M2.7-FB-2: contract references nested inside dict args are not seen, so a
    producer/consumer pair is co-scheduled.
  - F-M2.7-FB-4: lock keys are not hierarchical, so a directory lock does not
    exclude a descendant path.
  - F-M2.7-FB-5: effect ids are not normalised or validated.

Disk-verified anchors in `src/jarvis/kernel/manifest_dag.py` (440 lines @ 9a5b56d,
the file's only committed revision):
  - `_has_lock_conflict`  : def 217, write/write 227, write/read 230, read/write 233
  - `plan_execution_stages`: def 239, `ready_candidates.sort()` 268
  - `build_dag_from_manifest`: def 358, shallow `for val in args.values()` 384
  - `EffectNode`          : class 60, `id: str` 65
  - `validate_acyclic`    : def 145

Reference: the M2.7 red-team report circulated with anchors of 192-205 / 228-232 /
307-316 / 53-61. None of those resolve to the symbols it cited, in this revision or
any other. The anchors above are the ones a reader can actually follow.

Invariant 3 in the module docstring (:23-26) is the ground for FB-1 and FB-4:
"any two effects where at least one holds an exclusive write lock on resource R are
scheduled into distinct sequential execution stages."

PROPOSAL (F-M2.7-FB-2 fix constraint, not a test): dependency inference is currently
"any arg string equal to another contract's id" (:385-390). A recursive walker widens
that heuristic rather than fixing it, so it will fabricate edges from incidental
strings. The smallest close is to require the reference be declared (an explicit
`depends_on`, or a named key such as `source_contract`) and treat incidental matches
as data, not edges. `test_current_depth1_string_match_fabricates_a_dependency` below
records the constraint that has to be reasoned about either way.
"""

import sys

import pytest

from jarvis.kernel.intent import Budget, Manifest, ResolvedContract
from jarvis.kernel.manifest_dag import (
    EffectNode,
    build_dag_from_manifest,
    compile_from_manifest,
    plan_execution_stages,
    validate_acyclic,
)

ISO = "2026-09-21T00:00:00.000Z"

# macOS (APFS) and Windows (NTFS) are case-insensitive by default; Linux is not.
CASE_INSENSITIVE_FS = sys.platform.startswith("win") or sys.platform == "darwin"


def _manifest(contracts: list[ResolvedContract], manifest_id: str = "mf-m2-7") -> Manifest:
    """Minimal well-formed Manifest; mirrors the fixtures used by the committed probes."""
    return Manifest(
        manifest_id=manifest_id,
        intent_id="int-m2-7",
        contracts=contracts,
        required_capabilities=["c1"],
        budget=Budget(),
        constraints={},
        risk_class="safe",
        manifest_sha256="dummy",
        created_at_utc=ISO,
    )


# ---------------------------------------------------------------------------
# F-M2.7-FB-1 — lock canonicalisation
# ---------------------------------------------------------------------------


def test_invariant_scheme_case_variants_of_one_resource_are_exclusive() -> None:
    """F-M2.7-FB-1: a URI scheme is case-insensitive (RFC 3986 §3.1), so
    `file://workspace/out.txt` and `FILE://workspace/out.txt` are ONE resource.

    The requirement is platform-independent — it does not depend on the host
    filesystem being case-insensitive, because the two strings are the same URI
    everywhere. Two exclusive writers of one resource must not share a stage
    (module docstring Invariant 3, :23-26).

    Today: `_has_lock_conflict` (:227) compares raw strings, so both land in
    stage 0. RED until a canonical resource key exists.
    """
    a = EffectNode(id="w1", contract_id="write", write_locks=("file://workspace/out.txt",))
    b = EffectNode(id="w2", contract_id="write", write_locks=("FILE://workspace/out.txt",))

    stages = plan_execution_stages([a, b])

    assert len(stages) == 2, (
        "exclusive writers of one resource were co-scheduled: scheme case was treated "
        f"as a distinct resource key (stages={[s.effect_ids for s in stages]})"
    )


@pytest.mark.skipif(
    not CASE_INSENSITIVE_FS,
    reason="host filesystem is case-sensitive; case-variant paths are genuinely distinct resources",
)
def test_invariant_path_case_variants_of_one_path_are_exclusive() -> None:
    """F-M2.7-FB-1, second facet: on a case-insensitive filesystem the scheme-only
    fold above is not enough — path case must fold too, or the same file is still
    writable by two stages at once.

    RED today for the same reason as the probe above.
    """
    a = EffectNode(id="w1", contract_id="write", write_locks=("file://workspace/Out.txt",))
    b = EffectNode(id="w2", contract_id="write", write_locks=("file://workspace/out.TXT",))

    stages = plan_execution_stages([a, b])

    assert len(stages) == 2, (
        "on a case-insensitive filesystem these are one file, but the locks were "
        f"treated as distinct (stages={[s.effect_ids for s in stages]})"
    )


# ---------------------------------------------------------------------------
# F-M2.7-FB-2 — nested args dependency
# ---------------------------------------------------------------------------


def test_invariant_nested_args_contract_reference_creates_dependency() -> None:
    """F-M2.7-FB-2: `build_dag_from_manifest` documents that it extracts "data
    dependencies from args values matching other contract IDs" — it puts no bound
    on nesting. A reference reached only through a nested dict must therefore
    still produce an edge, and the consumer must be ordered strictly after the
    producer.

    Today: the walk at :384 is one level deep, so the edge is dropped and both
    effects are scheduled into stage 0. RED until the reference is seen.
    """
    manifest = _manifest(
        [
            ResolvedContract(id="producer", version="1.0.0", args={"output_file": "data.json"}),
            ResolvedContract(
                id="consumer",
                version="1.0.0",
                args={"pipeline_config": {"source_contract": "producer"}},
            ),
        ],
        manifest_id="mf-nested",
    )

    consumer = next(n for n in build_dag_from_manifest(manifest) if n.id == "consumer")

    assert "producer" in consumer.depends_on, (
        "a contract reference nested in a dict arg produced no dependency edge"
    )

    order = compile_from_manifest(manifest)
    assert order.concurrency_plan["consumer"] > order.concurrency_plan["producer"], (
        "consumer was not ordered after producer: "
        f"producer={order.concurrency_plan['producer']}, "
        f"consumer={order.concurrency_plan['consumer']}"
    )


# ---------------------------------------------------------------------------
# F-M2.7-FB-4 — hierarchical lock keys
# ---------------------------------------------------------------------------


def test_invariant_directory_lock_conflicts_with_descendant() -> None:
    """F-M2.7-FB-4: if a lock key may name a directory (`dir/`), then a lock on
    `dir/` and a lock on `dir/sub/file.txt` are locks on the SAME resource tree
    and must not share a stage (Invariant 3, :23-26).

    Today: both co-schedule. RED until lock keys carry containment semantics — or
    until the key grammar is declared opaque and this probe is deleted by ruling,
    not by edit.

    The boundary this fix must respect is pinned separately and green today by
    `test_current_sibling_prefix_is_not_a_descendant`.
    """
    dir_lock = EffectNode(id="dir_lock", contract_id="write", write_locks=("dir/",))
    descendant = EffectNode(id="file_read", contract_id="read", read_locks=("dir/sub/file.txt",))

    stages = plan_execution_stages([dir_lock, descendant])

    assert len(stages) == 2, (
        "a read of a directory's descendant was scheduled alongside an exclusive "
        f"write to that directory (stages={[s.effect_ids for s in stages]})"
    )


# ---------------------------------------------------------------------------
# F-M2.7-FB-5 — effect id normalisation
# ---------------------------------------------------------------------------


def _blank_id_is_rejected() -> bool:
    """True if a whitespace-only id is refused somewhere in the compile path.

    Deliberately fix-agnostic: rejecting at `EffectNode` construction and
    rejecting at `validate_acyclic` both close the finding.
    """
    try:
        node = EffectNode(id="   ", contract_id="test")
    except Exception:
        return True
    try:
        validate_acyclic([node])
    except Exception:
        return True
    return False


def test_invariant_blank_effect_id_is_rejected() -> None:
    """F-M2.7-FB-5: an effect id is an identity. A whitespace-only id is not a
    usable identity — it produces unreadable cycle traces and lets two nodes be
    distinct by invisible characters alone.

    Today: `EffectNode.id` (:65) is a bare `str`, and `validate_acyclic` (:145)
    accepts it. RED until the id is normalised or length-validated.
    """
    assert _blank_id_is_rejected(), (
        "a whitespace-only effect id was accepted at both EffectNode construction "
        "and validate_acyclic"
    )


# ---------------------------------------------------------------------------
# Current-behaviour companions (GREEN) — boundaries the fix must respect
# ---------------------------------------------------------------------------


def test_current_depth1_string_match_fabricates_a_dependency() -> None:
    """GREEN, must STAY green: inference is string equality against contract ids
    (:385-390), not a declared reference. `{"output_file": "producer"}` — a plain
    data argument that happens to spell a sibling contract's id — already creates
    an edge today.

    This is a characterisation, not a defect report: the module documents this
    inference. It is recorded so that F-M2.7-FB-2 is not closed by a deeper walker
    that silently makes the same fabrication reachable from any nesting depth.
    """
    manifest = _manifest(
        [
            ResolvedContract(id="producer", version="1.0.0", args={"output_file": "data.json"}),
            ResolvedContract(id="consumer", version="1.0.0", args={"output_file": "producer"}),
        ],
        manifest_id="mf-incidental",
    )

    consumer = next(n for n in build_dag_from_manifest(manifest) if n.id == "consumer")
    assert consumer.depends_on == ("producer",)


def test_current_sibling_prefix_is_not_a_descendant() -> None:
    """GREEN, must STAY green: a sibling path that merely shares a bare string
    prefix (`dir2/x.txt` vs `dir/`) is a DIFFERENT resource and must not conflict.

    Verified independently of the descendant probe, because a naive
    `startswith`-on-the-stripped-key close would satisfy FB-4 while failing this.
    """
    dir_lock = EffectNode(id="dir_lock", contract_id="write", write_locks=("dir/",))
    sibling = EffectNode(id="sibling", contract_id="write", write_locks=("dir2/x.txt",))

    assert len(plan_execution_stages([dir_lock, sibling])) == 1, (
        "a sibling path sharing a bare string prefix was treated as a descendant"
    )


def test_current_canonical_keys_are_in_place_and_declared_keys_are_preserved() -> None:
    """GREEN — inverted at fix time, not deleted.

    This began as a characterisation of the raw-string matching that was the open
    defect (F-M2.7-FB-1/FB-4). It now asserts the fixed behaviour, so the boundary
    stays pinned from both sides: writers of one resource are exclusive even when
    their declared spellings differ, AND `ExecutionStage` still records the keys as
    DECLARED rather than canonicalised.

    The second half is load-bearing. `tests/kernel/test_manifest_dag.py:198` asserts
    a stage records `("res://shared",)`; folding what gets recorded would be a
    silent change to a published field, which is why canonicalisation is
    comparison-only.
    """
    a = EffectNode(id="w1", contract_id="write", write_locks=("file://workspace/out.txt",))
    b = EffectNode(id="w2", contract_id="write", write_locks=("FILE://workspace/out.txt",))

    stages = plan_execution_stages([a, b])

    assert len(stages) == 2
    assert stages[0].write_locks == ("file://workspace/out.txt",)
    assert stages[1].write_locks == ("FILE://workspace/out.txt",)
