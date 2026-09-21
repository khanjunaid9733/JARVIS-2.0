from __future__ import annotations

"""Manifest Compilation & DAG Validation Engine (Milestone M2.7, spec §80.5 / §83 / §134.1).

Provides deterministic dependency validation, cycle detection, and parallel
vs. serial execution wave planning based on declared resource locks and explicit
dependencies.

Invariants:
1. Hermetic & Deterministic: No ambient clocks, no network calls, no model
   inference, and no filesystem I/O. Given identical effect nodes, compilation
   produces byte-identical execution plans and identical SHA-256 digests.
2. Strict Acyclicity: Any dependency cycle is detected and rejected with a
   typed `ManifestCycleError` detailing the exact cycle path.
3. Resource Lock Isolation:
   - Lock keys are compared through a canonical key (`canonical_resource_key`):
     the whole key is casefolded. That folds a URI scheme (RFC 3986 3.1, a scheme
     is case-insensitive) and is a deliberate over-approximation on
     case-sensitive filesystems - it costs parallelism, never safety, and it is
     what keeps a compiled digest identical across hosts.
   - Lock keys are hierarchical when slash-terminated: key `dir/` denotes a
     directory and contains `dir/sub/file.txt`, so a write on either excludes the
     other. A key without a trailing slash is opaque and contains nothing - which
     is what keeps `dir/` from swallowing the sibling prefix `dir2/`.
   - Shared read locks on the same resource key allow concurrent execution in the same wave.
   - Exclusive write locks require mutual exclusion: any two effects where at
     least one holds an exclusive write lock on a related resource R are
     scheduled into distinct sequential execution stages.
4. Deterministic Tie-Breaking: When multiple effects are topologically ready and
   conflict-free, they are sorted alphabetically by their unique node ID.
5. Identity: an effect id is a non-empty token without surrounding whitespace.
6. Stage Records: `ExecutionStage.read_locks` / `write_locks` always record the
   keys as DECLARED. Canonicalisation is for conflict comparison only.
7. Strictly Additive: Extends module 3 / `intent.py` ABI without altering existing
   frozen kernel modules.
"""

import enum
import hashlib
from typing import Any, Iterator, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .event_log import _canonical_json
from .intent import Manifest


# ---------------------------------------------------------------------------
# Resource Lock Definitions
# ---------------------------------------------------------------------------

class LockMode(str, enum.Enum):
    """Declared lock modes for effect resource access."""

    READ = "read"
    WRITE = "write"


class ResourceLock(BaseModel):
    """Declared resource lock requirement."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    resource: str
    mode: LockMode = LockMode.READ


# ---------------------------------------------------------------------------
# Canonical Resource Keys
# ---------------------------------------------------------------------------

def canonical_resource_key(resource: str) -> str:
    """Folds a declared lock key to its canonical COMPARISON form.

    The fold is total and platform-independent: the whole key is casefolded, so
    the URI scheme folds and so does the remainder. On a case-sensitive
    filesystem two paths differing only in case are genuinely two resources, so
    folding there serialises two effects that could have run together. That is a
    deliberate over-approximation on the side of safety, and it is what keeps a
    compiled digest identical across hosts.

    Used for CONFLICT COMPARISON ONLY. `ExecutionStage.read_locks` and
    `ExecutionStage.write_locks` always record the keys as declared.
    """
    return resource.strip().casefold()


def _key_contains(parent: str, child: str) -> bool:
    """True if canonical key `parent` denotes a directory holding `child`.

    Only a slash-terminated key denotes a directory. The trailing separator is
    load-bearing: it is what stops `dir/` from claiming the sibling `dir2/x.txt`.
    """
    return parent.endswith("/") and child != parent and child.startswith(parent)


# ---------------------------------------------------------------------------
# Effect Node Definition
# ---------------------------------------------------------------------------

class EffectNode(BaseModel):
    """A single effect node participating in a multi-effect manifest DAG."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    contract_id: str
    version: str = "1.0.0"
    depends_on: tuple[str, ...] = Field(default_factory=tuple)
    read_locks: tuple[str, ...] = Field(default_factory=tuple)
    write_locks: tuple[str, ...] = Field(default_factory=tuple)
    args: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _id_must_be_a_normalised_token(cls, value: str) -> str:
        """An effect id is an identity: non-empty, and not padded.

        A blank id produces unreadable cycle traces, and a padded id lets two
        nodes be distinct by invisible characters alone (duplicate detection is
        exact equality).
        """
        if not value.strip():
            raise ValueError("effect id must not be blank")
        if value != value.strip():
            raise ValueError(
                f"effect id {value!r} must not carry surrounding whitespace"
            )
        return value


# ---------------------------------------------------------------------------
# Typed Validation Errors
# ---------------------------------------------------------------------------

class ManifestCycleError(ValueError):
    """Raised when a dependency cycle is detected in the effect DAG."""

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = list(cycle)
        cycle_str = " -> ".join(self.cycle)
        super().__init__(f"Dependency cycle detected in effect manifest: {cycle_str}")


class DanglingDependencyError(ValueError):
    """Raised when an effect depends on an undefined effect ID."""

    def __init__(self, effect_id: str, missing_id: str) -> None:
        self.effect_id = effect_id
        self.missing_id = missing_id
        super().__init__(
            f"Effect '{effect_id}' depends on non-existent effect '{missing_id}'"
        )


class ConflictingLockDeclarationError(ValueError):
    """Raised when an effect declares conflicting read and write locks on the same resource."""

    def __init__(self, effect_id: str, resource: str) -> None:
        self.effect_id = effect_id
        self.resource = resource
        super().__init__(
            f"Effect '{effect_id}' declares conflicting read and write locks on resource '{resource}'"
        )


# ---------------------------------------------------------------------------
# Execution Plan Models
# ---------------------------------------------------------------------------

class ExecutionStage(BaseModel):
    """A parallel execution wave consisting of conflict-free effects."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    stage_index: int
    effect_ids: tuple[str, ...]
    read_locks: tuple[str, ...]
    write_locks: tuple[str, ...]


class CompiledWorkOrder(BaseModel):
    """Compiled, verified, and stage-ordered execution plan."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_id: str
    stages: tuple[ExecutionStage, ...]
    total_stages: int
    total_effects: int
    concurrency_plan: dict[str, int]
    dependency_graph: dict[str, list[str]]
    is_pure_serial: bool
    is_fully_parallel: bool
    max_concurrency: int
    dag_digest: str


# ---------------------------------------------------------------------------
# Core DAG Validation & Cycle Detection
# ---------------------------------------------------------------------------

def validate_acyclic(nodes: Sequence[EffectNode]) -> dict[str, set[str]]:
    """Validates that effect dependencies form a strict acyclic DAG.

    Checks:
      1. No duplicate effect IDs.
      2. No conflicting internal locks (read + write on identical resource in one node).
      3. All `depends_on` targets exist in `nodes`.
      4. No self-cycles (`A -> A`).
      5. No indirect cycles (`A -> B -> A`, `A -> B -> C -> A`).

    Returns:
      Mapping of `effect_id -> set(dependency_effect_ids)`.
    """
    node_map: dict[str, EffectNode] = {}
    for node in nodes:
        if node.id in node_map:
            raise ValueError(f"Duplicate effect ID '{node.id}' in manifest")
        node_map[node.id] = node

    # Check lock declarations and dependencies existence
    deps: dict[str, set[str]] = {}
    for node in nodes:
        # Check lock conflicts within single node
        read_keys = {canonical_resource_key(r) for r in node.read_locks}
        write_keys = {canonical_resource_key(w) for w in node.write_locks}
        overlap = read_keys.intersection(write_keys)
        if overlap:
            raise ConflictingLockDeclarationError(node.id, sorted(overlap)[0])

        node_deps: set[str] = set()
        for dep_id in node.depends_on:
            if dep_id not in node_map:
                raise DanglingDependencyError(node.id, dep_id)
            if dep_id == node.id:
                raise ManifestCycleError([node.id, node.id])
            node_deps.add(dep_id)
        deps[node.id] = node_deps

    # Cycle detection via DFS with 3-state tracking:
    # 0 = unvisited, 1 = visiting (on current path), 2 = visited
    state: dict[str, int] = {nid: 0 for nid in node_map}
    path: list[str] = []

    def dfs(u: str) -> None:
        state[u] = 1
        path.append(u)

        # Iterate deterministically over prerequisites
        for v in sorted(deps[u]):
            if state[v] == 1:
                # Cycle found: extract path from v to u, plus v
                idx = path.index(v)
                cycle_path = path[idx:] + [v]
                raise ManifestCycleError(cycle_path)
            if state[v] == 0:
                dfs(v)

        path.pop()
        state[u] = 2

    # Deterministic iteration order across all nodes
    for root_id in sorted(node_map.keys()):
        if state[root_id] == 0:
            dfs(root_id)

    return deps


# ---------------------------------------------------------------------------
# Execution Wave Planner (Parallel vs. Serial Scheduling)
# ---------------------------------------------------------------------------

def _has_lock_conflict(
    node: EffectNode,
    stage_reads: set[str],
    stage_writes: set[str],
) -> bool:
    """Checks whether a candidate node conflicts with locks already held in a stage.

    `stage_reads` / `stage_writes` hold CANONICAL keys. Two locks conflict when
    their canonical keys are related - equal, or one being a directory key that
    contains the other - and at least one of them is an exclusive write. Shared
    reads never conflict, at any depth of containment.
    """
    cand_reads = {canonical_resource_key(r) for r in node.read_locks}
    cand_writes = {canonical_resource_key(w) for w in node.write_locks}

    # Write-Write conflict
    if cand_writes.intersection(stage_writes):
        return True
    # Write-Read conflict (candidate writes, stage reads)
    if cand_writes.intersection(stage_reads):
        return True
    # Read-Write conflict (candidate reads, stage writes)
    if cand_reads.intersection(stage_writes):
        return True

    # Directory containment, candidate writes: excludes any held lock inside the
    # directory and any held directory holding the candidate.
    for cand_write in cand_writes:
        for held in stage_writes.union(stage_reads):
            if _key_contains(cand_write, held) or _key_contains(held, cand_write):
                return True

    # Directory containment, candidate reads: only an exclusive held WRITE can
    # exclude them (a directory of shared readers is still shared).
    for cand_read in cand_reads:
        for held_write in stage_writes:
            if _key_contains(cand_read, held_write) or _key_contains(held_write, cand_read):
                return True

    return False


def plan_execution_stages(nodes: Sequence[EffectNode]) -> tuple[ExecutionStage, ...]:
    """Schedules effect nodes into parallel execution waves (stages).

    Stages are constructed iteratively:
      1. Candidate nodes must have all prerequisites completed in prior stages.
      2. Candidate nodes are packed into the current stage if they do not conflict
         with locks held by any already-scheduled node in the stage.
      3. Tie-breaking is deterministic (alphabetical by node ID).
    """
    if not nodes:
        return ()

    deps = validate_acyclic(nodes)
    node_map: dict[str, EffectNode] = {n.id: n for n in nodes}

    completed: set[str] = set()
    remaining: set[str] = set(node_map.keys())
    stages: list[ExecutionStage] = []
    stage_index = 0

    while remaining:
        # Find all candidates whose dependencies are satisfied
        ready_candidates = [
            nid for nid in remaining if deps[nid].issubset(completed)
        ]
        if not ready_candidates:
            # Should not occur if graph is acyclic, but fail-closed safeguard
            raise RuntimeError("Deadlock in stage planning: no candidates ready")

        ready_candidates.sort()

        stage_effects: list[str] = []
        stage_reads: set[str] = set()
        stage_writes: set[str] = set()
        # Canonical mirrors, compared against but never recorded.
        held_read_keys: set[str] = set()
        held_write_keys: set[str] = set()

        for cand_id in ready_candidates:
            cand_node = node_map[cand_id]
            if not _has_lock_conflict(cand_node, held_read_keys, held_write_keys):
                stage_effects.append(cand_id)
                stage_reads.update(cand_node.read_locks)
                stage_writes.update(cand_node.write_locks)
                held_read_keys.update(
                    canonical_resource_key(r) for r in cand_node.read_locks
                )
                held_write_keys.update(
                    canonical_resource_key(w) for w in cand_node.write_locks
                )

        if not stage_effects:
            raise RuntimeError("Deadlock in stage planning: could not schedule any candidate")

        # Sort stage effects deterministically
        stage_effects.sort()

        stage = ExecutionStage(
            stage_index=stage_index,
            effect_ids=tuple(stage_effects),
            read_locks=tuple(sorted(stage_reads)),
            write_locks=tuple(sorted(stage_writes)),
        )
        stages.append(stage)

        completed.update(stage_effects)
        remaining.difference_update(stage_effects)
        stage_index += 1

    return tuple(stages)


# ---------------------------------------------------------------------------
# Manifest DAG Compilation
# ---------------------------------------------------------------------------

def compile_manifest_dag(
    manifest_id: str,
    nodes: Sequence[EffectNode],
) -> CompiledWorkOrder:
    """Compiles effect nodes into a validated, stage-ordered `CompiledWorkOrder`."""
    stages = plan_execution_stages(nodes)
    total_stages = len(stages)
    total_effects = len(nodes)

    concurrency_plan: dict[str, int] = {}
    for stage in stages:
        for eid in stage.effect_ids:
            concurrency_plan[eid] = stage.stage_index

    dependency_graph: dict[str, list[str]] = {
        node.id: sorted(list(set(node.depends_on)))
        for node in sorted(nodes, key=lambda n: n.id)
    }

    is_pure_serial = all(len(stage.effect_ids) <= 1 for stage in stages)
    is_fully_parallel = total_stages <= 1
    max_concurrency = max((len(stage.effect_ids) for stage in stages), default=0)

    # Compute deterministic canonical SHA-256 digest
    digest_payload = {
        "manifest_id": manifest_id,
        "stages": [stage.model_dump() for stage in stages],
        "total_stages": total_stages,
        "total_effects": total_effects,
        "concurrency_plan": concurrency_plan,
        "dependency_graph": dependency_graph,
    }
    dag_digest = hashlib.sha256(_canonical_json(digest_payload)).hexdigest()

    return CompiledWorkOrder(
        manifest_id=manifest_id,
        stages=stages,
        total_stages=total_stages,
        total_effects=total_effects,
        concurrency_plan=concurrency_plan,
        dependency_graph=dependency_graph,
        is_pure_serial=is_pure_serial,
        is_fully_parallel=is_fully_parallel,
        max_concurrency=max_concurrency,
        dag_digest=dag_digest,
    )


# ---------------------------------------------------------------------------
# Manifest Adapter Entrypoint
# ---------------------------------------------------------------------------

def _iter_string_leaves(value: Any) -> Iterator[str]:
    """Yields every string reachable inside a container, at any depth.

    A contract reference is a reference wherever it appears, so the walk is
    recursive over mappings and sequences rather than one level deep.

    Known limitation, left documented rather than papered over: matching is
    still plain string equality against contract ids, so an incidental argument
    that happens to spell a sibling contract's id still creates an edge. Recursion
    widens the reach of that heuristic rather than removing it; closing it
    properly means requiring a declared reference, which is a design change, not a
    walk change. See `tests/review/test_freebuff_invariants_m2_7.py`.
    """
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for nested in value.values():
            yield from _iter_string_leaves(nested)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _iter_string_leaves(item)


def build_dag_from_manifest(manifest: Manifest) -> list[EffectNode]:
    """Converts a standard `jarvis.kernel.intent.Manifest` into a list of `EffectNode`s.

    Extracts:
      - Explicit dependencies from contract args (`depends_on` or `_depends_on`).
      - Data dependencies from args values matching other contract IDs.
      - Read and write locks from contract args (`read_locks`, `write_locks`).
    """
    contract_ids = [rc.id for rc in manifest.contracts]
    contract_id_set = set(contract_ids)

    nodes: list[EffectNode] = []
    for rc in manifest.contracts:
        args = rc.args or {}

        # 1. Extract dependencies
        explicit_deps: set[str] = set()
        raw_deps = args.get("depends_on") or args.get("_depends_on")
        if isinstance(raw_deps, str):
            explicit_deps.add(raw_deps)
        elif isinstance(raw_deps, (list, tuple, set)):
            for d in raw_deps:
                if isinstance(d, str):
                    explicit_deps.add(d)

        # Search for contract references anywhere inside args values, at any depth
        for val in args.values():
            for candidate in _iter_string_leaves(val):
                if candidate in contract_id_set and candidate != rc.id:
                    explicit_deps.add(candidate)

        # 2. Extract resource locks
        raw_reads = args.get("read_locks") or args.get("_read_locks") or []
        if isinstance(raw_reads, str):
            read_locks = (raw_reads,)
        else:
            read_locks = tuple(sorted({str(r) for r in raw_reads}))

        raw_writes = args.get("write_locks") or args.get("_write_locks") or []
        if isinstance(raw_writes, str):
            write_locks = (raw_writes,)
        else:
            write_locks = tuple(sorted({str(w) for w in raw_writes}))

        nodes.append(
            EffectNode(
                id=rc.id,
                contract_id=rc.id,
                version=rc.version,
                depends_on=tuple(sorted(explicit_deps)),
                read_locks=read_locks,
                write_locks=write_locks,
                args=args,
            )
        )

    return nodes


def compile_from_manifest(manifest: Manifest) -> CompiledWorkOrder:
    """Convenience compiler converting and compiling a `Manifest` into a `CompiledWorkOrder`."""
    nodes = build_dag_from_manifest(manifest)
    return compile_manifest_dag(manifest.manifest_id, nodes)


__all__ = [
    "CompiledWorkOrder",
    "ConflictingLockDeclarationError",
    "DanglingDependencyError",
    "EffectNode",
    "ExecutionStage",
    "LockMode",
    "ManifestCycleError",
    "ResourceLock",
    "build_dag_from_manifest",
    "canonical_resource_key",
    "compile_from_manifest",
    "compile_manifest_dag",
    "plan_execution_stages",
    "validate_acyclic",
]
