# M5.1 — Hierarchical Task Network (HTN) Planner (Kickoff & Design Contract)

**Status:** PROPOSAL — contract to ratify before any `src/` change.  
**Author/owner:** Big Pickle (OpenCode) implements; Freebuff attacks; Antigravity verifies.  
**Milestone:** M5 (Embodiment & External Device Nodes), package M5.1 (of `docs/M5_KICKOFF.md`).  
**Baseline:** `task/supervisor @ 1fcfdf4`, **814 passed**, M0–M4 frozen.  
**Proof Target (M5.1):** `goal -> HTN decomposition -> domain method selection -> DAG validation -> MissionPlan`.  

---

## 1. Why This Exists

In `src/jarvis/live.py`, task planning relies on `_LocalDecomposer`, which emits a hardcoded three-step linear pipeline (`plan -> deliver -> attest`). While sufficient to prove the composition root, real autonomous cognitive operation across device nodes requires **dynamic, context-sensitive planning**.

Hierarchical Task Networks (HTN) are deterministic, provably verifiable, and avoid open-ended model hallucination:
- Goals decompose into high-level **Compound Tasks**.
- Tasks map to **Domain Methods** whose preconditions must evaluate against the current state (from `MemoryProjection`).
- Methods resolve into **Primitive Operators** (executable steps) that declare required **Resource Locks** and postcondition **Effects**.
- Emitted plan integrates directly with `src/jarvis/kernel/manifest_dag.py` for parallel wave scheduling and cycle validation.

---

## 2. Grounding in the Frozen Modules

- **`src/jarvis/kernel/manifest_dag.py`**: Static acyclic dependency validation, parallel execution waves, resource lock conflict detection.
- **`src/jarvis/orchestrator/mission_runner.py`**: `MissionPlan` and `MissionStep` execution ratchet.
- **`src/jarvis/kernel/memory_projection.py`**: State facts and state digest (`NAT-03`) providing grounded world state for precondition checks.
- **`src/jarvis/kernel/intent.py`**: Validated contract proposals and schemas.

---

## 3. Design Contract (To Be Ratified)

### A. Data Structures (`src/jarvis/kernel/planner/types.py`)

```python
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

@dataclass(frozen=True)
class Precondition:
    name: str
    predicate: Callable[[Mapping[str, Any]], bool]
    description: str

@dataclass(frozen=True)
class PrimitiveOperator:
    id: str
    summary: str
    action_type: str
    required_locks: tuple[str, ...] = ()
    expected_effects: tuple[str, ...] = ()
    parameters: Mapping[str, Any] = None

@dataclass(frozen=True)
class DomainMethod:
    name: str
    task_name: str
    preconditions: tuple[Precondition, ...]
    subtasks: tuple[str, ...]  # May reference compound tasks or primitive operator IDs

@dataclass(frozen=True)
class HTNDomain:
    name: str
    methods: tuple[DomainMethod, ...]
    operators: tuple[PrimitiveOperator, ...]
```

### B. The HTN Planner Engine (`src/jarvis/kernel/planner/htn.py`)

```python
class HTNPlanner:
    def __init__(self, domain: HTNDomain) -> None:
        self.domain = domain

    def plan(
        self,
        goal_task: str,
        world_state: Mapping[str, Any],
        max_depth: int = 16,
    ) -> Sequence[PrimitiveOperator]:
        """Deterministically decompose goal_task into primitive operators.
        
        Raises:
            PlanningFailure: If preconditions fail or no valid decomposition exists.
            RecursionLimitExceeded: If decomposition exceeds max_depth (cycle protection).
        """
        ...
```

### C. Mission Plan Adapter (`src/jarvis/kernel/planner/adapter.py`)

```python
class HTNDecomposer:
    """Implements the Decomposer protocol expected by MissionRunner and LiveRuntime."""
    def __init__(self, planner: HTNPlanner, state_provider: Callable[[], Mapping[str, Any]]) -> None:
        self.planner = planner
        self.state_provider = state_provider

    def decompose(self, goal: str) -> tuple[MissionStep, ...]:
        ...
```

---

## 4. Deterministic Invariants for M5.1

1. **Cycle Prevention**: Circular task expansions must be detected fail-closed and raise `RecursionLimitExceeded` rather than infinite-looping.
2. **Deterministic Tie-Breaking**: When multiple methods satisfy preconditions, selection follows strict declaration order in `HTNDomain.methods`.
3. **DAG Compatibility**: The emitted sequence must compile into an acyclic `ManifestDAG` with zero lock violations.
4. **Memory State Purity**: Precondition checks are read-only and may never mutate the state.

---

## 5. Paste-Ready Kickoff Prompt for Big Pickle (OpenCode)

```markdown
# M5.1 Implementation Assignment — OpenCode (Big Pickle)

You are Big Pickle, primary implementation engineer for JARVIS 2.0.
Workspace: `F:\JARVIS2.0`
Branch: `task/supervisor`
Baseline: `1fcfdf4` (814 passed, clean working tree).

Task:
Implement M5.1 (Hierarchical Task Network Planner & Decomposer) per `docs/M5_1_KICKOFF.md`:
1. Create `src/jarvis/kernel/planner/types.py` (Precondition, PrimitiveOperator, DomainMethod, HTNDomain).
2. Create `src/jarvis/kernel/planner/htn.py` (HTNPlanner with backtracking and cycle detection).
3. Create `src/jarvis/kernel/planner/adapter.py` (HTNDecomposer integrating with `MissionStep`).
4. Create test suite in `tests/kernel/test_htn_planner.py` covering:
   - Successful multi-tier decomposition
   - Precondition failure fallback
   - Circular recursion detection
   - Deterministic method tie-breaking
   - ManifestDAG compilation compatibility
5. Ensure all existing 814 tests remain 100% green.
```
