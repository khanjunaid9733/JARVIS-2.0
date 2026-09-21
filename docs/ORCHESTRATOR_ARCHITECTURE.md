# JARVIS Agent Orchestrator — Proposed Architecture v1.0

**Status:** PROPOSED — design accepted pending implementation evidence. Not "Frozen."
**Promotes to Frozen v1.0 only after:** Phase 0 verified + Phases 1–2 implemented + T1–T10 passing + recovery demonstrated.
**Authority:** creator approval gates merge/push. Nothing below overrides that.

---

## 0. Ground truth

| Claim | Status |
|---|---|
| `task/m2.1 @ af99696`, 312 passed | Verified (merged to main) |
| M2.2 merged (`e417de3`), 385 passed | Verified on disk |
| M2.3 merged (`82085c1`), 413 passed | Verified on disk |
| M2.4 on `task/m2.4`, 420 passed | Verified on disk (awaiting creator merge ruling) |
| `agy` headless interface | **VERIFIED** — `agy.exe -p`, `--dangerously-skip-permissions`, `--add-dir` present on PATH |
| Modules 1–17 frozen at `frozen/m1.1 @ 160a3c2` | Verified |

---

## 1. Thesis

> **Agents produce proposals. The decision plane produces acceptance. Nothing crosses except measured facts.**

An agent saying "done" is a *proposal*. An exit code, a tree hash, a test count from a machine-readable artifact, a git object id — those are *facts*. The entire design exists to keep those two categories from ever being confused. This is `NAT-05` ("the model proposes, determinism disposes") applied to the development loop itself.

---

## 2. Invariants

Any implementation that violates one is wrong.

| # | Invariant |
|---|---|
| **I1** | No proposal-plane process may write decision-plane state. Enforced by state living **outside the repository**, owned by the supervisor process. |
| **I2** | A worker cannot reach `ACCEPTED`. Only the Verification Authority produces that transition. |
| **I3** | The frozen baseline is an **immutable tag/commit**, never `main`. |
| **I4** | The orchestrator is fully functional with `AGY_BRIDGE = unavailable`. |
| **I5** | No provider fills two roles for the same package (red-team ≠ verifier). |
| **I6** | No history rewrite. Revert is a new commit. |
| **I7** | Merge and push require explicit creator approval. |
| **I8** | Dispatch is idempotent: a crash between intent and start never double-launches. |
| **I9** | Verification operates on a **frozen commit**, never a live worktree. |
| **I10** | The Verification Authority is referenced from an **immutable commit**, not a self-hash of the file currently executing. |

---

## 3. The two planes

```
┌───────────────────── PROPOSAL PLANE (untrusted) ─────────────────────┐
│  LLM workers: Big Pickle · Freebuff · Antigravity · specialists       │
│  Emit: diffs · tests · findings · plans · reports                     │
│  Run in: disposable worktrees, capability-sandboxed, no state access  │
│  Cannot: write journal · write verify · merge · push · touch frozen   │
└───────────────────────────────┬───────────────────────────────────────┘
                                │  artifacts + exit codes + commit ids
                                ▼
┌───────────────────── DECISION PLANE (trusted) ───────────────────────┐
│  Deterministic Python: verify · journal · ledger · scheduler ·       │
│  router · supervisor.  No LLM executes here.                          │
│  Reads facts. Emits verdicts. Advances state.                         │
└───────────────────────────────────────────────────────────────────────┘
```

**Physical enforcement (I1):** decision-plane state lives outside the repo, owned by the supervisor process:

```
F:\JARVIS_ORCHESTRATOR_STATE\
    journal\dev.jsonl          # append-only, hash-chained, durable
    verify\M2.5.json           # gate artifacts
    ledger\                    # derived cache (never authoritative)
    proposals\                 # COMMIT_PROPOSAL records awaiting creator
    leases\                    # active worker leases (L4)
    logs\<worker_id>\          # stdout/stderr, preserved on death
```

A shared worktree cannot enforce I1; a separate directory tree plus process ownership can.

---

## 4. Layer map

```
L7  Bridges           opencode · agy · deepseek           ← unverified edge
L6  Supervisor        fold → dispatch → gate → advance
L5  Router            role contract → capability → exclusion → provider
L4  Worker            disposable worktree + sandbox + lease + heartbeat
L3  Scheduler         scope graph + concurrency + budgets
L2  Ledger            derived state (cache)
L1  Journal           append-only hash chain (source of truth)
L0  Verification Authority   the acceptance mechanism
```

Dependencies strictly downward. **L6 is a pure function of L1 + wall clock.** No in-memory state that isn't reconstructible from the journal.

---

## 5. L0 — Verification Authority

The acceptance mechanism. No agent involved. Human-runnable.

```
scripts/verify.py --package M2.5 --commit <sha> --baseline frozen/m1.1
                   --out F:\JARVIS_ORCHESTRATOR_STATE\verify\M2.5.json
```

Executes in order, fail-fast:

1. **Suite** — `uv run pytest -q`; count parsed machine-readably.
2. **Frozen baseline check** — every path under `src/jarvis/kernel/**` that existed at the baseline tag must be byte-identical **unless listed in the package's `allowed_paths`**. Compared against the *tag*, never `main` (I3).
3. **Probe check** — all `tests/review/**` probes for this package must pass.
4. **Authority fingerprint** — recorded from an immutable reference (I10), not a self-hash of the running file.
5. **Digest** — `sha256` over canonical summary + commit.

**I10 correction — the verifier does not hash itself:**

```yaml
verification_authority:
  commit:       <immutable commit that contains verify.py>
  tree_sha256:  <hash of that tree>
  verify_py_sha256: <hash at that commit>
  python_version:   "3.12.x"
  dependency_lock_hash: <uv.lock / requirements hash>
```

The gate resolves **its own code from an immutable git reference**, then verifies the commit under test. A mutable working copy of `verify.py` has no authority. This closes the "verifier modified between runs" hole.

Artifact:

```json
{
  "artifact_type": "verification",
  "package": "M2.5",
  "attempt_id": "M2.5-a1",
  "input_commit": "af99696",
  "verified_commit": "3c9d1f2",
  "frozen_baseline": { "tag": "frozen/m1.1", "commit": "160a3c2" },
  "verification_authority": {
    "commit": "…", "tree_sha256": "…", "verify_py_sha256": "…",
    "python_version": "3.12.x", "dependency_lock_hash": "…"
  },
  "suite":        { "passed": true, "count": 312, "failed": 0 },
  "frozen_check": { "passed": true, "violations": [] },
  "probes":       { "total": 4, "passing": 4 },
  "digest": "sha256:…",
  "exit": 0
}
```

**Rule (closes the hallucinated-completion class):** the supervisor reads only this file. It never parses pytest stdout. It never reads an agent's completion message.

`frozen_check.passed == false` → `FAILED_FROZEN_BREACH`, no retry, escalate (I3/I6).

---

## 6. L1 — Journal

**Durability contract (not a storage implementation):**

```
append(record):
    canonicalize (sorted keys, no whitespace — same as event_log._canonical_json)
    write
    flush
    fsync
    → only then acknowledge the state transition
```

The architecture preserves these semantics regardless of physical storage:

```
JournalRecord · Append · Replay · Hash-chain · Durability
```

JSONL is the **current implementation**, not the contract. JARVIS M3 can later back this with `EventLog` while preserving the five semantics above.

Event vocabulary (closed set):

```
DISPATCH_INTENT · DISPATCH_STARTED · DISPATCH_COMPLETED
STAGE_START · STAGE_COMPLETE · THROTTLED · DEGRADED
LEASE_GRANTED · LEASE_RENEWED · LEASE_EXPIRED
STALLED · TERMINATED · ARTIFACT_FREEZE
VERIFY_RESULT · REPAIR · HOLD
COMMIT_PROPOSAL · CREATOR_APPROVED · CREATOR_REJECTED
MERGED · REVERTED
```

Every dispatch-related event carries `supervisor_instance_id` (§13).

---

## 7. L2 — Ledger

Folded from L1 on every supervisor wake. Never written directly.

```
task_id · package · stage · role · worker_id
attempt_id · dispatch_id · lease_id
state · provider · input_commit · output_commit · branch · worktree
attempt · max_attempts · started · deadline · heartbeat
tokens_used · cost · artifacts[] · gate_result · failure_reason
supervisor_instance_id
```

---

## 8. L3 — Scheduler

Three gates before any dispatch:

1. **Concurrency cap** — `MAX_ACTIVE = 3` to start (1 builder, 1 reviewer, 1 specialist). The value is correctness, not throughput.
2. **Scope graph** — each package declares `allowed_paths`; two concurrent packages may **not** overlap. Example: M2.7 (`intent*.py`) and M2.8 (`authority*.py`, `identity*.py`) don't overlap → co-schedulable. If both touched `registry.py` → serialize.
3. **Budgets** — per task: max tokens, wall-clock, retries. Enforced here, not in the worker.

Dependency edges from the M2 package list. Dispatch only what is `READY` **and** scope-clear **and** in budget.

**Reserved paths (never worker-writable):** `docs/MASTER_BUILD_SPEC.md`, `AGENTS.md`, `project_state.yaml`, `docs/FROZEN_MODULES.yaml`, `scripts/**`. Written only by the supervisor/integrator. Kills the concurrent `project_state.yaml` conflict class.

---

## 9. L4 — Worker, lease, and sandbox

```
1. worktree:  F:\JARVIS_WORKTREES\<pkg>\<role>-<worker_id>\   (disposable)
2. lease:     granted (see below)
3. sandbox:   capability grant applied
4. spawn:     provider via bridge
5. heartbeat: poll every N seconds; journal PROGRESS
6. on COMPLETION_REQUESTED → ARTIFACT_FREEZE → commit → verify the commit
7. journal outcome
8. git worktree remove --force   (never reuse across packages)
```

**Lease (the correction that makes restart handling clean):**

```yaml
lease_id:     lease-<ulid>
worker_id:    w-7f3a
task_id:      M2.5
supervisor_instance_id: sup-20260919-001
expires_at:   <ts>
renewed_at:   <ts>
```

The lease distinguishes four states the supervisor must tell apart:

| Observation | Meaning |
|---|---|
| lease valid + heartbeat fresh | worker genuinely running |
| lease valid + heartbeat stale | supervisor lost contact → `STALLED` |
| lease expired + supervisor_instance_id ≠ current | stale worker from a prior supervisor |
| two workers, same `task_id`, different `lease_id` | duplicate → kill the older |

**Sandbox (replaces `--dangerously-skip-permissions` entirely):**

| Control | Mechanism |
|---|---|
| allowed paths | separate local user + deny-write ACE, or container; defense-in-depth |
| allowed commands | allowlist wrapper; no arbitrary shell by default |
| network | default deny; explicit egress allow for the model endpoint only |
| timeout / budget | wall-clock + token/cost kill |
| cancellation | supervisor SIGTERM → grace → SIGKILL |

Because I9 verifies a **commit**, immutability holds by content-addressing regardless of ACLs. ACLs are defense-in-depth, not the primary guarantee.

**Death handling:**

```
heartbeat stale → STALLED → collect logs → terminate
                → git reset --hard && git clean -fdx   ← MANDATORY
                → journal STALLED + LEASE_EXPIRED
                → reassign (attempt+1) | HOLD
```

Without the hard reset, an automated system reproduces the "40 minutes lost to an unterminated string" bug, silently and at scale.

---

## 10. L5 — Router and role contracts

**Roles are capability contracts, not provider names.** The architecture must survive Big Pickle disappearing.

```
IMPLEMENTER          → implementation.v1
RED_TEAM_REVIEWER    → redteam.v1
INDEPENDENT_VERIFIER → verification.v1
RECONCILER           → reconciliation.v1
```

Resolution order — **never by availability alone**:

```
role contract → required capabilities → exclusion constraints
             → provider behavioral profile (trust, cost, latency, health)
             → provider
```

The provider registry maps *current* fulfillment, separate from the contract:

```
provider registry:
    bigpickle   currently satisfies implementation.v1, reconciliation.v1
    freebuff    currently satisfies redteam.v1
    antigravity currently satisfies redteam.v1, verification.v1
```

**Exclusion constraint (I5):**

```
∀ package P:
  provider_filling(redteam.v1, P)
    ≠
  provider_filling(verification.v1, P)
```

Antigravity may red-team package A and verify package B. It may **never** do both for the *same* package. Enforced in the router, journalled, unit-tested.

**Fallback:** when every provider for a role is unavailable → `stage = DEGRADED`, `covered_by = null`, **package HOLDS**. It does not advance to merge. A package that skipped adversarial review is *pending*, not done.

**Provenance naming:** if Antigravity fills a red-team slot, the artifact is `docs/M2_5_REDTEAM.md`, never `…_FB.md`. Never let a filename claim a provider that didn't produce it.

---

## 11. L6 — Supervisor

A pure fold over the journal:

```
loop:
  ledger = fold(journal)
  for RUNNING:              check lease / heartbeat / deadline / budget
  for READY:                check scope / concurrency / budget → dispatch
  for COMPLETION_REQUESTED: ARTIFACT_FREEZE → verify → accept | repair | hold
  for REPAIR:               reassign IMPLEMENTER (gate artifact as input)
  append decisions to journal
  sleep(interval)
```

**Pipeline (corrected terminal):**

```
IMPLEMENT → RED_TEAM → VERIFY → RECONCILE → VERIFY
    → COMMIT_PROPOSAL → AWAIT_CREATOR → MERGE → (PUSH)
```

The supervisor's terminal autonomous action is `COMMIT_PROPOSAL`. Merge and push require creator approval (I7). **Tests passing is necessary, not sufficient.**

**Circuit breakers, priority order:**

| Condition | Action |
|---|---|
| frozen-module breach | `FAILED_FROZEN_BREACH` — immediate, no retry, escalate |
| same failure ×3 | `HOLD`, escalate |
| wall-clock / cost cap | `TERMINATED`, worktree reset, journal |
| retry cap (3) | `HELD` |
| otherwise | repair, attempt+1 |

---

## 12. L7 — Bridges (the unverified edge)

```python
class Bridge(Protocol):
    def submit(self, prompt: str, workdir: Path, sandbox: Sandbox) -> Handle: ...
    def status(self, handle: Handle) -> WorkerStatus: ...
    def cancel(self, handle: Handle) -> None: ...
    def collect(self, handle: Handle) -> Artifacts: ...
```

| Bridge | Command | Status |
|---|---|---|
| opencode | `opencode run "<prompt>"` (no `-p`) | verify before use |
| agy | `agy -p "<prompt>" --dangerously-skip-permissions --add-dir "<dir>"` | **VERIFIED on disk** (Phase 0) |
| deepseek | via opencode provider config / direct API | verify before use |

---

## 13. Idempotency, supervisor identity, and recovery

**Every dispatch event carries `supervisor_instance_id`:**

```yaml
supervisor_instance_id: sup-20260919-001
```

This lets recovery distinguish the current supervisor, a previous crashed supervisor, and an unknown orphan.

**Dispatch protocol (I8):**

```
1. journal DISPATCH_INTENT  {dispatch_id, task, role, provider, sup_id}  ← fsync
2. spawn worker
3. journal DISPATCH_STARTED {dispatch_id, worker_id, handle, sup_id}     ← fsync
4. … run …
5. journal DISPATCH_COMPLETED {dispatch_id, output_commit}
```

**Recovery on restart:**

| Journal state | Meaning | Action |
|---|---|---|
| `INTENT` only | spawn may or may not have happened | mark `UNKNOWN`, kill orphan by `worker_id`, reset worktree, retry with **new** `dispatch_id` |
| `INTENT` + `STARTED` | orphan worker | terminate, `reset --hard`, `clean -fdx`, retry |
| `STARTED` + `COMPLETED` | normal | continue |

The intent is journalled *before* the side effect, so a crash window leaves a detectable trace rather than a double-launch.

---

## 14. Repo integration and the frozen baseline

**Baseline is a tag, not a branch:** `frozen/m1.1 @ 160a3c2`. As each M2 package merges, a new tag `frozen/m2.<n>` is cut, and `verify.py` compares against the *latest* frozen tag. `main` is never the reference (I3).

**Frozen set rule:** any path present at the baseline tag is frozen unless listed in the package's `allowed_paths`. Automatic — no hand-maintained manifest to drift.

**Reserved (never worker-writable):** `docs/MASTER_BUILD_SPEC.md`, `AGENTS.md`, `project_state.yaml`, `docs/FROZEN_MODULES.yaml`, `scripts/**`.

**Revert protocol (I6):** a bad merge is undone by a new `revert` commit, never `reset`/`rebase`/`force-push`. The journal records `REVERTED`.

---

## 15. State machines

**Worker (with `LEASED`):**

```
CREATED → ASSIGNED → LEASED → STARTING → RUNNING
RUNNING              → COMPLETION_REQUESTED
COMPLETION_REQUESTED → ARTIFACT_FREEZE        ← worktree → commit, locked
ARTIFACT_FREEZE      → VERIFICATION
VERIFICATION         → ACCEPTED | REPAIR | INFRA_FAILURE
REPAIR               → RUNNING (attempt+1)
INFRA_FAILURE        → RETRY | HOLD
RUNNING              → (lease expiry) STALLED → TERMINATED
```

**Task:**

```
PROPOSED → RATIFIED → READY → RUNNING → AWAIT_GATE
AWAIT_GATE → RECONCILING → AWAIT_GATE
AWAIT_GATE → COMMIT_PROPOSAL → AWAIT_CREATOR → MERGED | REJECTED
any        → DEGRADED | HELD | FAILED
```

**Provider health:** `UNKNOWN → AVAILABLE → RATE_LIMITED → COOLDOWN → PROBE → AVAILABLE | EXHAUSTED`. Uses `Retry-After` + exponential backoff; **one** probe after the expected reset. Never hammers the endpoint. `429 ≠ permanently unavailable`.

---

## 16. Build order

| Phase | Deliverable | Exit criterion |
|---|---|---|
| **0** | Environment discovery | `agy` interface known or explicitly absent — **DONE** |
| **1** | **Verification Authority** (`verify.py`, schema) | correct artifact on pass, fail, frozen-breach |
| **2** | **Journal + replay** (`journal.py`) | T3, T4 pass |
| **3** | **Single worker** (one package, one role, one worktree) | T1, T2 pass; one package driven end-to-end manually |
| **4** | **Recovery** | **T5** — kill/restart/orphan/reconcile → exactly-once |
| **5** | Role contracts + provider router | T6 pass |
| **6** | Scheduler + parallelism | T8, T10; two scope-clear packages co-scheduled |
| **7** | Antigravity integration | T7 (degraded path) + AGY path if interface exists |
| **8** | Autonomous overnight mode | unattended run + morning report |
| **9** | Absorb into JARVIS M3 | role contracts map onto the capability registry |

---

## 17. Test specification

| # | Test | Guards |
|---|---|---|
| T1 | Gate rejects modified frozen module | I3 |
| T2 | Gate rejects when probes fail | L0 completeness |
| T3 | Journal replay reconstructs exact state | L1 |
| T4 | Crash between intent and start → no double launch | I8 |
| T5 | **Kill supervisor mid-dispatch → restart → replay → detect orphan → reconcile → continue exactly once** | I8, recovery |
| T6 | Same provider cannot fill two roles for one package | I5 |
| T7 | Orchestrator completes a package with `AGY` unavailable | I4 |
| T8 | Stall → terminate → worktree reset → reassign | L4 |
| T9 | Creator approval gate blocks merge | I7 |
| T10 | Budget exceeded → terminate, no merge | L3 |
| T11 | Verifier tampered between runs → artifact rejected | I10 |

---

## 18. Why this is also JARVIS work

| Orchestrator | JARVIS kernel |
|---|---|
| role contracts | capability registry / `Manifest` |
| provider router | `ProviderResolver` + adapter seam |
| Verification Authority | `done_gate` / NAT-05 |
| event journal | `EventLog` |
| task ledger | `MemoryProjection` |
| worker lifecycle | `mission_lifecycle` FSM |
| capability sandbox | `EffectEnvelopeEngine` authorize |
| `COMMIT_PROPOSAL → approval` | irreversible-effect verification |

---

## 19. What this is not

- **Not a throughput play at M2 scale.** ~6 sequential packages sharing one frozen boundary. Parallelism pays off at M3/M4 when workstreams are genuinely independent.
- **Not a replacement for the creator gate.** Merge and push stay human. Load-bearing, not caution.
- **Not dependent on Antigravity.** I4 makes that structural.
- **Not frozen yet.** Proposed v1.0 — promotes to Frozen only after evidence.
