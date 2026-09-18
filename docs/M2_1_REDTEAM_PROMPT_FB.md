# Freebuff — Adversarial Review Prompt (M2.1)
## Milestone 2: Memory OS — Package M2.1 (Memory API + Episodic Trace)

### 0. Role and Hard Constraints
You are **Freebuff / DeepSeek**, the adversarial architecture & research reviewer.
Your findings are **PROPOSALS**, not accepted architecture.
- You **may** add test files under `tests/` and docs under `docs/` as evidence.
- You **must not** modify anything under `src/` — not even a docstring.
- You **must not** merge, rebase, push, or commit anything except your own added `tests/`/`docs/` evidence. Do not rewrite history; do not delete files.
- Do not restate the code back. Produce findings with concrete failure traces and reproducible evidence.

### 1. Target (Verify First — STOP if it does not match)
- Branch: `task/m2.1`
- Base commit: **`af99696`** (`feat(kernel): M2.1 memory API + episodic trace (contract A-E ratified)`)
- Preconditions to verify:
  - Working tree: clean (or only containing uncommitted audit documentation)
  - `uv run --with pytest --with opentelemetry-sdk --with opentelemetry-api --with anyio pytest -q` → **312 passed, 0 failed** in ~16s
- If the commit or the test count differ, **stop and report the mismatch**.

### 2. Read Before Attacking
- `AGENTS.md` (Universal Rules; rule 10 = no history rewrites)
- `docs/DECISIONS.md` — ADR-001..010
- `docs/MASTER_BUILD_SPEC.md` — §84.3 (two-tier consolidation), §84.4 (memory verification ladder), §85.2 (projections), §M2
- `docs/M2_KICKOFF.md` — M2 proof: `read file → evidence → memory trace → restart → recover`
- `docs/M2_1_KICKOFF.md` — Ratified design contract (items A–E)
- `docs/M2_1_AUDIT.md` — Antigravity's independent verification audit (`F-M2.1-1` through `F-M2.1-5`)
- Target code under review:
  - `src/jarvis/kernel/memory_trace.py` (MemoryTraceWriter, TraceWriteResult)
  - `src/jarvis/kernel/memory_index.py` (MemoryIndex projection, NAT-03 digest)
  - `src/jarvis/kernel/memory_api.py` (Memory facade, recall, get, digest)
  - `src/jarvis/cli.py` (`_cmd_recall`)
  - Tests in `tests/kernel/test_memory_trace.py`, `test_memory_index.py`, `test_memory_api.py`, `tests/test_cli.py`

### 3. Attack Surfaces — Find where these break; do not confirm they exist

**A. Episodic Trace Writer (`src/jarvis/kernel/memory_trace.py`)**
1. **Causal Discipline**: `cause_event_id = evidence[-1] if evidence else None`. What happens when `evidence` contains invalid event IDs, empty strings, cyclic references, or non-list iterables?
2. **DoneGate Coupling**: Trace tier borrows `DoneGate` kind `"memory.write"`. Does the shape of episodic evidence diverge from durable semantic memory? Can a malicious or malformed trace payload cause an unhandled exception before the gate evaluates?
3. **Correlation Semantics**: If `correlation_id` is omitted, it defaults to the trace event's newly generated ULID. When a trace is part of a multi-step mission or saga, does it properly chain?

**B. Combined Projection (`src/jarvis/kernel/memory_index.py`)**
1. **Stream Sequence & Replay Ordering**: `MemoryIndex._from_events` iterates over `log.replay()`. Does it handle duplicate event IDs, payload type mismatches, or out-of-order stream sequences?
2. **Projection Partitioning**: Memories and traces are stored in separate dictionaries (`memories` and `traces`). Can an event ID collision occur between the two?
3. **NAT-03 State Digest**: Rebuild twice yields identical digest. Can a log be crafted where `MemoryIndex.digest()` drifts across Python versions, dict key orderings, or object serialization?

**C. Memory Facade (`src/jarvis/kernel/memory_api.py`)**
1. **Union Recall Scoring & Bias**: `recall()` pools memories and traces into a single duck-typed `_CombinedView`. Does lexical token overlap favor short episodic traces over long semantic memories, or vice versa?
2. **Tie-Break Determinism**: Tie-breaking is specified as `(-score, event_id)`. If two memories (or a memory and a trace) have identical token overlap scores, is the ordering stable across platforms?
3. **Fallbacks & Projections**: `Memory` accepts `log`, `index`, or `projection`. Test the edge cases: empty index, empty log, missing keys, or calling `get()` on deleted/non-existent events.

**D. CLI Surface (`src/jarvis/cli.py`)**
1. **Offline Hermeticity**: Verify `jarvis recall` works offline with zero network or provider connections.
2. **Output Contract**: Test formatting stability with multiline content, unicode, or empty queries.

### 4. Deliverable
A structured adversarial report in `docs/M2_1_REDTEAM_FB.md` following the repo's severity taxonomy (CRITICAL / HIGH / MEDIUM / LOW), citing exact file:line references and test cases that demonstrate the failure modes.
