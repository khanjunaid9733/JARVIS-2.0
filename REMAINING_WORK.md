# JARVIS 2.0 — COMPREHENSIVE ROADMAP & REMAINING WORK

> **Repository Root:** `F:\JARVIS2.0`  
> **Active Branch:** `task/supervisor` @ `9a5b56d`  
> **Last Verified:** September 21, 2026  
> **Test Suite Status:** **711 passed in 39.49s**, 0 failed (100% GREEN)  
> **Orchestrator State:** `F:\JARVIS_ORCHESTRATOR_STATE\`

---

## ⚠️ CRITICAL NOTICE FOR ALL AI AGENTS & SESSIONS

> [!CAUTION]
> **DO NOT USE OR TOUCH `C:\Users\khanj\jarvis_home` OR `C:\Users\khanj\Downloads`**  
> Any files found in `C:\Users\khanj\jarvis_home` (such as `JARVIS_BUILD_COMPLETE.md`, `START_JARVIS_COMPLETE_SETUP.bat`, or monolithic 31-system scripts) are **deprecated December 2025 prototypes**.  
> The true, production-grade JARVIS 2.0 system lives exclusively in **`F:\JARVIS2.0`**.  
> When starting a session, always ensure your working directory is `F:\JARVIS2.0` (`cd F:\JARVIS2.0`).

---

## 1. Executive Summary & Verified Ground Truth

JARVIS 2.0 is an immutable, event-sourced, persistent cognitive operating system governed by **`AGENTS.md`** and **`docs/MASTER_BUILD_SPEC.md`**.  
The core architecture follows the foundational principle: **"The model proposes; determinism disposes."** AI models (OpenCode / Freebuff / Antigravity) produce untrusted proposals, while the deterministic kernel and supervisor enforce invariants, verification, and state transitions.

### Verified State Table

| Milestone / Component | Commit / Tag | Status | Test Count |
|---|---|---|---|
| **M0: Spec & Repo Setup** | `frozen/m0` | VERIFIED | — |
| **M1: Core Deterministic Kernel** (Modules 1–13) | `df72c4a` / `1a1311d` | VERIFIED & FROZEN | 243 passed |
| **M1.1: Stretch Modules** (Modules 14–17: Mission FSM, Model Answering, Budgets, Explain) | `frozen/m1.1 @ 160a3c2` | VERIFIED & FROZEN | 292 passed |
| **M2.1: Memory API & Episodic Trace** | `af99696` | VERIFIED & MERGED | 312 passed |
| **M2.2: Embedding & Retrieval Seams** | `e417de3` | VERIFIED & MERGED | 385 passed |
| **M2.3: Memory Consolidation Pipeline** | `82085c1` | VERIFIED & MERGED | 413 passed |
| **M2.4: Hermetic Verification Ladder** | `afa6beb` (on `main`) | VERIFIED & MERGED | 420 passed |
| **M2.5: PII Seam & Data Privacy Policy** | `07a30a1` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | 682 passed |
| **M2.6: Hermetic Filesystem Effect & Sandbox** | `c908ea4` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | 692 passed |
| **M2.7: Manifest Compilation & DAG Validation** | `9a5b56d` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | **711 passed** |
| **M3.1: Autonomous Engineering Supervisor** | `98a82bd` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | 548 passed |
| **M3.2: Multi-Step Mission Execution Loop** | `98a82bd` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | 564 passed |
| **M3.3: Dynamic Worker Orchestration & L7 Bridges** | `ce605bc` (on `task/supervisor`) | **VERIFIED & RECONCILED** | 629 passed |
| **M3.4: Automated Failure Recovery & Rollback Engine** | `0f43bcf` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | 590 passed → 629 (reconciled) |
| **M3.5: Supervisor Daemon (Lease/Heartbeat + Orphan Recovery + Ledger Fold)** | `15c4fe9` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | 664 passed |

---

## 2. What Is Already Implemented & Verified

### A. The Deterministic Kernel & Effects Layer — FROZEN
- **Event Log (`event_log.py`)**: SQLite-backed append-only hash-chained event store with cryptographic tamper detection.
- **Creator Identity (`creator_identity.py`)**: Principal identification and authority boundaries.
- **Intent ABI (`intent_abi.py`)**: Schema-validated intent declarations with static validation.
- **Capability Registry (`registry.py`)**: Dynamic provider registry with semantic versioning and substitution seams.
- **Model Gateway (`gateway.py`)**: Model-agnostic invocation with fallback failover.
- **Memory Projection (`memory_projection.py`)**: Deterministic projection state and SHA-256 state digest (`NAT-03`).
- **Effect Envelope (`effect_envelope.py`)**: Prepare-authorize-commit-verify two-phase effect execution.
- **Policy Engine (`policy.py`)**: Static and runtime viability checks (budget, privacy, risk).
- **Done Gate (`done_gate.py`)**: Deterministic completion gate enforcing evidence before `task.completed`.
- **Mission Lifecycle (`mission_lifecycle.py`)**: Deterministic lifecycle FSM folding over event streams.
- **Budget Ledger (`budget_ledger.py`)**: Mission and session token/cost accounting fold.
- **PII Seam & Privacy Policy (`privacy.py`)**: Deterministic data classification, regex/pattern-based PII detection/redaction, and fail-closed privacy gate.
- **Filesystem Effect & Sandbox (`src/jarvis/effects/filesystem.py`)**: Path-jailed filesystem operations behind `EffectEnvelopeEngine`, atomic writes with pre-mutation backup, and byte-identical rollback.
- **Manifest DAG & Compilation (`src/jarvis/kernel/manifest_dag.py`)**: Static acyclic dependency validation, cycle detection, and parallel vs. serial execution wave planning based on declared resource locks.

### B. Autonomous Engineering Supervisor (`src/jarvis/supervisor/`)
1. **`authority.py`**: Deterministic L0/L1/L2 authority tiers and escalation classification (9 reasons).
2. **`evidence.py`**: 7-tier precedence ladder (`FILESYSTEM=7` down to `AGENT_MEMORY=1`) and conflict resolution.
3. **`lifecycle.py`**: 9-state task lifecycle FSM with absorbing `FROZEN_SUCCESS`.
4. **`mutation_guard.py`**: Byte-level SHA-256 tree fingerprinting to detect post-verification tampering.
5. **`recovery.py`**: Deterministic ladder fold (`NONE`, `RETRY`, `RESTART`, `ROLLBACK`, `ESCALATE`, `HOLD`).
6. **`supervisor.py`**: Verifier, Observer, and Acceptor protocols; decision synthesis.

### C. Deterministic Verification & State Harness (`scripts/`)
- **`scripts/verify.py`**: Independent L0 Verification Authority. Enforces pytest run, compares frozen baseline against commit `7607a6f`, runs review probes, captures authority fingerprint, and emits canonical JSON evidence.
- **`scripts/journal.py`**: Append-only hash-chained fsync-durable JSONL journal.
- **`scripts/supervisor.py`**: CLI orchestrator (`init`, `status`, `verify`) enforcing single-writer locks (`supervisor.lock`) and durable ledger updates (`ledger.json`).
- **Milestones M3.1–M3.5, M2.5, M2.6 & M2.7 Accepted**: Recorded in `F:\JARVIS_ORCHESTRATOR_STATE\evidence\M3.1.json`, `M3.2.json`, `M3.3.json`, `M3.4.json`, `M3.5.json`, `M2.5.json`, `M2.6.json`, and `M2.7.json`.

---

## 3. Detailed Breakdown of Remaining Work

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        REMAINING WORK ROADMAP                          │
├───────────────────┬───────────────────┬────────────────────────────────┤
│    MILESTONE      │       SCOPE       │           STATUS               │
├───────────────────┼───────────────────┼────────────────────────────────┤
│ M2 Residuals      │ M2.8 – M2.10      │ Active focus (M2.5-2.7 sealed) │
│ M3 Orchestrator   │ M3.1 – M3.5       │ ✅ 100% COMPLETE & FROZEN      │
│ M4 Multimodal     │ Vision / Voice    │ Planned after M2 residuals     │
│ M5 Robotics       │ Physical Nodes    │ Long-term directional          │
└───────────────────┴───────────────────┴────────────────────────────────┘
```

### Phase 1: Milestone M2 Residuals (Memory & Capability Hardening)

#### 1. M2.5 — PII Seam & Data Privacy Policy (`src/jarvis/kernel/privacy.py`) [COMPLETED & FROZEN]
- [x] Implement data classification tags (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`).
- [x] Add automatic regex and pattern-based redaction filters on memory trace ingestion.
- [x] Enforce fail-closed privacy checks in `PrivacySanitizer` before writing to persistent projections.
- [x] Unit tests: Prove that unredacted PII is rejected or redacted, and audit events are emitted (18 tests).

#### 2. M2.6 — Hermetic Filesystem Effect & Sandbox (`src/jarvis/effects/filesystem.py`) [COMPLETED & FROZEN]
- [x] Sandbox file manipulation behind `EffectEnvelopeEngine`.
- [x] Enforce path jail (operations restricted strictly to project workspace).
- [x] Implement atomic write-with-backup and rollback capability for filesystem mutations.
- [x] Unit tests: Verify path traversal attempts fail and rollback restores byte-identical state (10 tests).

#### 3. M2.7 — Manifest Compilation & DAG Validation (`src/jarvis/kernel/manifest_dag.py`) [COMPLETED & FROZEN]
- [x] Static acyclic dependency validation for multi-effect intent manifests (`validate_acyclic`).
- [x] Parallel vs. serial effect execution planner based on declared resource locks (`plan_execution_stages`).
- [x] Manifest adapter and deterministic work order digest (`compile_manifest_dag`, `compile_from_manifest`).
- [x] Unit tests: Cycle detection in effect graphs, deterministic topological sort, lock conflict scheduling (19 tests).

#### 4. M2.8 — Key-Based Creator Authority (`src/jarvis/kernel/crypto_authority.py`)
- [ ] Ed25519 signature verification for creator-gated actions (reopen, merge proposal, policy override).
- [ ] Replace simple `principal_id == "creator"` string equality with cryptographic signature verification (`NAT-02` complete).
- [ ] Unit tests: Prove that tampered signatures or forged keys are rejected with `AuthorityUnavailable`.

#### 5. M2.9 — Dynamic Budgets & Circuit Breakers (`src/jarvis/kernel/circuit_breaker.py`)
- [ ] Sliding-window rate limiters for external model and API providers.
- [ ] Dynamic budget enforcement: hard token/cost ceiling per session and per mission.
- [ ] Automatic trip to `HOLD` when error rates exceed threshold.
- [ ] Unit tests: Invariant tests under simulated provider outages and token exhaustion.

#### 6. M2.10 — Unified Memory Checkpoint & Single State Digest (`src/jarvis/kernel/checkpoint.py`)
- [ ] Unify `MemoryIndex.digest()` with `MemoryProjection.digest()`.
- [ ] Implement incremental checkpointing: snapshot projection state to disk with hash chain verification.
- [ ] Cold-start hydration: restart from checkpoint + replay tail of event log.
- [ ] Unit tests: Prove cold-start recovery produces byte-identical memory state in <100ms.

---

### Phase 2: Milestone M3 — Autonomous Engineering Orchestrator

#### 1. M3.2 — Multi-Step Mission Execution Loop (`src/jarvis/orchestrator/mission_runner.py`) [COMPLETED & FROZEN]
- [x] Autonomous task decomposition: split high-level user goal into ordered subtasks (`Decomposer` seam).
- [x] Deterministic step progression through `TaskLifecycle` FSM (`TASK_APPROVED` → `IMPLEMENTING` → `WORKER_VERIFY` → `PASS` → `FROZEN_SUCCESS`).
- [x] Integration with `scripts/verify.py` and `StepVerifier` seam for automated step-by-step acceptance.
- [x] Deterministic recovery fold (`RETRY` / `RESTART` / `ROLLBACK` / `ESCALATE` / `HOLD`) bounded by `RecoveryPolicy`.
- [x] 16 unit tests passing in `tests/orchestrator/test_mission_runner.py`.

#### 2. M3.3 — Dynamic Worker Orchestration & L7 Bridges (`src/jarvis/orchestrator/bridges/` & `router.py`) [COMPLETED, RECONCILED & FROZEN]
- [x] **OpenCode Bridge (`opencode.py`)**: Automated task dispatch via OpenCode CLI.
- [x] **Freebuff Bridge (`deepseek.py`)**: Adversarial red-team dispatch for automated vulnerability reviews.
- [x] **Antigravity Bridge (`agy.py`)**: Independent audit and test suite execution via `agy.exe`.
- [x] **Router & Role Contracts (`router.py`)**: Capability contracts (`implementation.v1`, `redteam.v1`, `verification.v1`, `reconciliation.v1`).
- [x] **Invariant I5 Enforcement**: Strict exclusion preventing a provider from both red-teaming and verifying the same package.
- [x] **Freebuff Red-Team Reconciled**: Closed FB-1 (sandbox validation), FB-2 (process containment & kill-on-close Job Object on Windows), FB-3 (async lifecycle & real cancel), FB-4 (canonical provider/package identity + alias table), FB-6 (prompt length ceiling), FB-7 (thread-safe atomic job transitions).
- [x] 18 review probes passing in `tests/review/test_freebuff_redteam_m3_3.py`.

#### 3. M3.4 — Automated Failure Recovery & Rollback Engine (`src/jarvis/orchestrator/recovery_engine.py`) [COMPLETED & FROZEN]
- [x] Hook `decide_recovery()` ladder directly into git worktree operations.
- [x] Automated `RETRY` with failure context injection into worker prompt.
- [x] Automated `ROLLBACK` to `last_known_good` commit upon repeated verification failure.
- [x] Automated `ESCALATE` generating human-actionable escalation bundles.
- [x] 12 unit tests passing in `tests/orchestrator/test_recovery_engine.py`.

#### 4. M3.5 — Supervisory Daemon Decision Plane (`src/jarvis/orchestrator/daemon.py`) [COMPLETED & FROZEN]
- [x] Lease/heartbeat adjudication (FRESH / STALLED / ORPHANED / DUPLICATE) per §9 four-state table.
- [x] Dispatch-trace recovery fold per §13 restart table (INTENT-only → UNKNOWN, INTENT+STARTED → ORPHAN, STARTED+COMPLETED → NORMAL, retry with NEW dispatch_id).
- [x] `ledger.json` maintained as a pure fold over `journal.jsonl` (never written directly).
- [x] Hermetic `SupervisorDaemon.run_tick` decision engine - effects only through an injected `Effects` seam.
- [x] 35 unit tests passing in `tests/orchestrator/test_daemon.py`. Suite 664 green = 310 kernel + 121 supervisor + 98 orchestrator + 84 review probes + 21 bootstrap/CLI + 15 acceptance + 15 providers.
- [x] **F-M3.3-FB-2 hardening follow-up**: `ContainedProcess.terminate()` on Windows now runs `taskkill /F /T` from the live parent FIRST (closes the `_popen`→`assign(pid)` race where a grandchild escaped the Job Object). Verified stable across repeated full-suite runs.

---

### Phase 3: Milestone M4 — Multimodal Cognition (Vision & Speech)

- [ ] **Voice Interface**: Local Whisper STT + Piper TTS behind versioned provider adapters.
- [ ] **Vision Processing**: Local vision model adapter (e.g. CLIP / Moondream) for screenshot and diagram analysis.
- [ ] **Streaming Event Loop**: Real-time event subscription for low-latency voice turn-taking.

---

### Phase 4: Milestone M5 — Embodiment & External Device Nodes

- [ ] Phone node integration via lightweight RPC.
- [ ] IoT and hardware peripheral control contracts behind provider adapters.
- [ ] Distributed event log synchronization across nodes.

---

## 4. How to Start a New Agent Session (Big Pickle / OpenCode)

When initiating work in a new session:

```bash
# 1. Switch to the authoritative workspace
cd F:\JARVIS2.0

# 2. Verify git branch and status
git status
# (Must be on branch: task/supervisor)

# 3. Check orchestrator status and current milestone
uv run python scripts/supervisor.py status

# 4. Verify test suite health (must be 664 passing)
uv run pytest -q

# 5. Read context documents before making any changes
# - docs/KICKOFF_NEW_SESSION.md
# - docs/ORCHESTRATOR_ARCHITECTURE.md
# - project_state.yaml
```

### Verification Command for Any Completed Package:
```bash
uv run python scripts/supervisor.py verify <PACKAGE_NAME>
```
*(Example: `uv run python scripts/supervisor.py verify M3.2`)*

---

## 5. Non-Negotiable Operating Rules

1. **Kernel Immutability**: Never touch `src/jarvis/kernel/` without an explicit architectural decision record (ADR).
2. **Authority Hierarchy**: Creator (L2) approval is required for all merges to `main` and pushes to `origin`.
3. **Deterministic Acceptance**: No package is complete until `scripts/supervisor.py verify <pkg>` exits `0` and emits a signed evidence bundle.
4. **No Test Weakening**: Never weaken, disable, or delete existing tests to force a pass.
