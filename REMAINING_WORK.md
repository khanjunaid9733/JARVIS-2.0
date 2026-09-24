# JARVIS 2.0 — COMPREHENSIVE ROADMAP & REMAINING WORK

> **Repository Root:** `F:\JARVIS2.0`  
> **Active Branch:** `task/supervisor`  
> **Last Verified:** September 24, 2026  
> **Test Suite Status:** **793 passed in 43.54s**, 0 failed (100% GREEN; 785 before the live loop)  
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
| **M2.7: Manifest Compilation & DAG Validation** | `31d7a55` (on `task/supervisor`) | **VERIFIED & RECONCILED** | 721 passed |
| **M2.8: Key-Based Creator Authority** | `8a481c2` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | 744 passed |
| **M2.9: Dynamic Budgets & Circuit Breakers** | `9c2b265` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | 758 passed |
| **M2.10: Unified Memory Checkpoint & Single State Digest** | `5b0a792` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | 766 passed |
| **M3.1: Autonomous Engineering Supervisor** | `98a82bd` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | 548 passed |
| **M3.2: Multi-Step Mission Execution Loop** | `98a82bd` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | 564 passed |
| **M3.3: Dynamic Worker Orchestration & L7 Bridges** | `ce605bc` (on `task/supervisor`) | **VERIFIED & RECONCILED** | 629 passed |
| **M3.4: Automated Failure Recovery & Rollback Engine** | `0f43bcf` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | 590 passed → 629 (reconciled) |
| **M3.5: Supervisor Daemon (Lease/Heartbeat + Orphan Recovery + Ledger Fold)** | `15c4fe9` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | 664 passed |
| **M4: Multimodal Cognition (Vision & Speech)** | `70d535f` (on `task/supervisor`) | **VERIFIED & ACCEPTED** | **785 passed** |

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

### D. Live Loop / Composition Root (`src/jarvis/live.py`, `jarvis mission` / `jarvis voice`) — NEW (uncommitted)

Every milestone above M1 shipped as an importable, unit-tested fold with no caller: there were zero non-test constructors of `MissionRunner`, `Router`, `RecoveryEngine` and `SupervisorDaemon`, and zero importers of `jarvis.multimodal`. `src/jarvis/live.py` is that caller and nothing else — the smallest wiring that makes the system runnable:

```bash
cd F:\JARVIS2.0
export JARVIS_HOME=$(mktemp -d)          # any clean home
uv run --frozen jarvis init
uv run --frozen jarvis mission "keep the kernel deterministic under load" --fault deliver=1
uv run --frozen jarvis mission "keep the kernel deterministic under load" --worker external --worker-timeout 60
uv run --frozen jarvis voice "when does the deploy gate run"        # speaks: real WAV written beside the log
uv run --frozen jarvis voice "ignored" --audio question.wav          # real STT + real per-frame VAD
uv run --frozen jarvis recall "deploy gate"
```

One goal runs `intake -> decompose -> dispatch -> verify -> recover -> recall`: a real `mission.started` event, a declared ordered plan, Router role resolution on canonical identities (I5 applied), per-step dispatch precondition validation with real dispatch traces, artifacts written atomically inside the workspace jail through the effect envelope, independent filesystem verification of the bytes, the supervisor recovery ladder + ACT plane (`--fault step=N` proves a RETRY really re-executes the worker with the failure bytes carried), a `SupervisorDaemon` tick over the real dispatch records and mission lease, NAT-05 completion (or refusal), and a memory write + recall. With `--worker external` the step is dispatched to a REAL external process through the L7 bridge (`WorkDatum` carries the real handle, PID, exit code and containment: `precondition` | `spawn-fault` | `timeout` | `self-attested` | `failed`), and the artifact is adjudicated by an `IndependentVerifier` in a fresh process attributed to a *different* provider - the worker's own return value is never read, so Invariant I5 is exercised instead of asserted. `jarvis voice` runs the real 6-state turn-taking FSM journaled on stream `voice-session`, transcribes real audio through whichever engine is bound, answers from memory, speaks the answer through a real synthesis engine (measured, non-silent WAV written beside the log), and reports every component as `real` or `seam` in one honest line.

A voice turn also SPEAKS: the first real synthesis engine on this machine is bound (`JARVIS_TTS_CMD` contract unchanged, then `piper`, then the Windows OS engine `System.Speech`, then `espeak-ng`) and the payload is measured before it counts - a WAV is parsed for duration/rate/peak/RMS and a silent or non-WAV payload is reported as a FAILED synthesis with no file written. With `--audio <wav>` the input side stops being a flag: the file is sliced into real 30ms frames whose activity is the measured RMS energy of those samples, and the FSM's collected buffer holds those bytes.

Named seams (reported in the command output, never as verified): no microphone device is opened (a typed turn declares `caller-declared` VAD and says nothing was captured; real audio in needs `--audio <file>`) and the turn writes its WAV beside the log without opening a speaker; the default worker is local (labelled `local (in-process, NOT a dispatch)`) and no external engine on this machine can produce an artifact - `opencode run` never returns non-interactively (200-240s, empty output, exit 124) and `agy -p` exits 0 while reporting every tool call blocked by a malformed global plugin hook path, so `--worker external` ends in containment timeout plus `task.completion_refused`; the recovery git rollback seam is not injected (ROLLBACK declared, never executed); vision stays library-only; mic capture/VAD are caller-declared. External worker containment is process-tree containment, not a filesystem sandbox: the jail governs what may be *accepted*, not what the engine may touch (`network_allowed` / `max_memory_mb` are declared, unenforced).

### E. Multimodal Cognition (`src/jarvis/multimodal/`)
- **Voice Interface (`voice.py`)**: `WhisperSTTAdapter` (`audio.transcribe` v1.0.0) + `PiperTTSAdapter` (`audio.synthesize` v1.0.0) implementing `ProviderAdapter` with pluggable runner seams.
- **Vision Processing (`vision.py`)**: `VisionModelAdapter` (`vision.describe`, `vision.analyze` v1.0.0) implementing `ProviderAdapter`.
- **Streaming Event Loop (`streaming.py`)**: `VoiceTurnState` 6-state machine (`IDLE`, `LISTENING`, `USER_SPEAKING`, `THINKING`, `ASSISTANT_SPEAKING`, `INTERRUPTED`) and `StreamingVoiceLoop` with real-time barge-in interruption handling and event log auditing.

---

## 3. Detailed Breakdown of Remaining Work

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        REMAINING WORK ROADMAP                          │
├───────────────────┬───────────────────┬────────────────────────────────┤
│    MILESTONE      │       SCOPE       │           STATUS               │
├───────────────────┼───────────────────┼────────────────────────────────┤
│ M2 Residuals      │ M2.8 – M2.10      │ ✅ 100% COMPLETE & FROZEN      │
│ M3 Orchestrator   │ M3.1 – M3.5       │ ✅ 100% COMPLETE & FROZEN      │
│ M4 Multimodal     │ Vision / Voice    │ ✅ 100% COMPLETE & FROZEN      │
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

#### 4. M2.8 — Key-Based Creator Authority (`src/jarvis/kernel/crypto_authority.py`) [COMPLETED & FROZEN]
- [x] Ed25519 signature verification for creator-gated actions (reopen, merge proposal, policy override).
- [x] Replace simple `principal_id == "creator"` string equality with cryptographic signature verification (`NAT-02` complete).
- [x] Unit tests: Prove that tampered signatures or forged keys are rejected with `AuthorityUnavailable` (23 tests).

#### 5. M2.9 — Dynamic Budgets & Circuit Breakers (`src/jarvis/kernel/circuit_breaker.py`) [COMPLETED & FROZEN]
- [x] Sliding-window rate limiters for external model and API providers.
- [x] Dynamic budget enforcement: hard token/cost ceiling per session and per mission.
- [x] Automatic trip to `HOLD` when error rates exceed threshold.
- [x] Unit tests: Invariant tests under simulated provider outages and token exhaustion (14 tests).

#### 6. M2.10 — Unified Memory Checkpoint & Single State Digest (`src/jarvis/kernel/checkpoint.py`) [COMPLETED & FROZEN]
- [x] Unify `MemoryIndex.digest()` with `MemoryProjection.digest()` into single memory-tract digest (FB-2 / NAT-03).
- [x] Implement incremental checkpointing: snapshot projection state to disk with hash chain verification.
- [x] Cold-start hydration: restart from checkpoint + replay tail of event log.
- [x] Unit tests: Prove cold-start recovery produces byte-identical memory state in <100ms (8 tests).

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

### Phase 3: Milestone M4 — Multimodal Cognition (Vision & Speech) [COMPLETED & FROZEN]

- [x] **Voice Interface**: Local Whisper STT (`audio.transcribe` v1.0.0) + Piper TTS (`audio.synthesize` v1.0.0) behind versioned `ProviderAdapter`s.
- [x] **Vision Processing**: Local vision model adapter (CLIP / Moondream behind `vision.describe` and `vision.analyze` v1.0.0) implementing `ProviderAdapter`.
- [x] **Streaming Event Loop**: Real-time event subscription for low-latency voice turn-taking with barge-in interruption handling (`StreamingVoiceLoop`).
- [x] 19 unit tests passing across `tests/multimodal/test_voice.py`, `tests/multimodal/test_vision.py`, and `tests/multimodal/test_streaming.py`.

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

# 4. Verify test suite health (must be green; 793 at the live-loop pass)
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
