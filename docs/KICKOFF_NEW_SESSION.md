# KICKOFF CONTEXT: NEW AGENT SESSION

> **Purpose:** Provide immediate, high-signal ground truth for any fresh OpenCode (Big Pickle) or agent session starting on `task/supervisor`. Read this document first before inspecting files.

---

## 1. Machine-Verified Ground Truth

| Datum | Verified Reality | Status |
|---|---|---|
| **Directory** | `F:\JARVIS2.0` (NEVER use `C:\Users\khanj\jarvis_home`) | ACTIVE WORKSPACE |
| **Branch** | `task/supervisor` @ `98a82bd` | ACTIVE |
| **Main Baseline** | `main` @ `afa6beb` (M2.4 merged) | FROZEN |
| **Baseline Commit** | `7607a6f1f226824b5a7038e15efd66932529da7c` | IMMUTABLE |
| **Core Kernel** | `src/jarvis/kernel/**` byte-identical to `main` | UNTOUCHED (0 diffs) |
| **Test Suite** | **629 passed in 37.45s**, 0 failed | 100% GREEN |
| **Active Plan** | M3 Orchestrator / Autonomous Engineering Supervisor | IN PROGRESS |
| **State Directory** | `F:\JARVIS_ORCHESTRATOR_STATE\` | INITIALIZED & ACTIVE |
| **Frozen Packages** | `["M3.1", "M3.2", "M3.3", "M3.4"]` (signed in `evidence/`) | ACCEPTED |

---

## 2. What Is Already Implemented & Verified

### A. The Supervisor Package (`src/jarvis/supervisor/`)
All 6 contract modules + `__init__.py` exist and export 26 symbols:
1. **`authority.py`**: `AuthorityTier` (L0, L1, L2), `EscalationReason` (9 reasons), `decide_authority_tier(reason)`, `is_creator_gated(reason)`. Pure data, deterministic lookup.
2. **`evidence.py`**: `EvidenceSource` (7 rungs), `EvidencePrecedence` (`FILESYSTEM=7` down to `AGENT_MEMORY=1`), `Evidence`, `EvidenceLedger` (`with_entry`, `highest`, `authority`, `conflicts`), `VerificationResult`.
3. **`lifecycle.py`**: `LifecycleState` (9 states), `LifecycleEvent` (14 events), `TaskLifecycle` FSM, `lifecycle_transitions` table. `FROZEN_SUCCESS` is absorbing; only creator-gated `REOPEN` moves it.
4. **`mutation_guard.py`**: `PackageSnapshot` (`folder_fingerprint`), `MutationReport` (`mutated`, `added`, `removed`, `changed`), `MutationGuard` (`seal`, `check`).
5. **`recovery.py`**: `RecoveryAction` (`NONE`, `RETRY`, `RESTART`, `ROLLBACK`, `ESCALATE`, `HOLD`), `RecoveryPolicy`, `RecoveryPlan`, `decide_recovery(...)`. Pure data ladder fold.
6. **`supervisor.py`**: `Verifier`, `Observer`, `Acceptor` protocols; `SupervisorDecision`; `Supervisor` (`decide`, `verify`, `freeze`).

### B. Unit & Integration Tests (`tests/supervisor/`, `tests/orchestrator/`, `tests/review/`)
All suites passing (629 tests total):
* `tests/supervisor/`: 9 test files (121 tests)
* `tests/orchestrator/`: 4 test files (42 tests: `mission_runner`, `bridges`, `router`, `recovery_engine`)
* `tests/review/`: 4 review probe files (including Freebuff's 18 M3.3 probes)

### C. Verification & Orchestration Scripts (`scripts/`)
* **`scripts/verify.py`**: Phase 1 L0 Verification Authority. Enforces pytest suite, compares frozen baseline against commit `7607a6f`, executes review probes, collects authority fingerprint, and emits canonical SHA-256 digested JSON evidence.
* **`scripts/journal.py`**: Append-only, hash-chained, fsync-durable JSONL journal (`journal.jsonl`).
* **`scripts/supervisor.py`**: CLI orchestrator (`init`, `status`, `verify`). Enforces single-writer lock (`supervisor.lock`), durable ledger (`ledger.json`), and coordinates verify + journal emission.

### D. Milestones M3.1, M3.2, M3.3 & M3.4 Verified & Frozen
* Evidence bundles:
  - `F:\JARVIS_ORCHESTRATOR_STATE\evidence\M3.1.json` (`sha256:82234d7554342760aaaea6d496e911de7980550bfc9e719f0b051316a4c0d057`)
  - `F:\JARVIS_ORCHESTRATOR_STATE\evidence\M3.2.json` (`sha256:c7a757db846c04815c73071513e83217a58b7a0450a0760d3e0578821b05777a`)
  - `F:\JARVIS_ORCHESTRATOR_STATE\evidence\M3.3.json` (`sha256:51634863eeeb4c82ce94c5892e72f51ca0a1ae303b58635015def77ede55c603`)
  - `F:\JARVIS_ORCHESTRATOR_STATE\evidence\M3.4.json` (`sha256:bdf8ec16a4c1ee78ed55bc391d6ec9eaf062ae3a53be14e5375b3b04ed3a22a5`)
* Ledger updated: `frozen_packages: ["M3.1", "M3.2", "M3.3", "M3.4"]`, `last_known_good: "0f43bcfa9c9e257a4b4e6adc710a456d223a038d"`, `last_verify_exit: 0`.

---

## 3. Critical Context on Past Failures (Do Not Repeat)

1. **WRONG DIRECTORY**: NEVER look for or edit files in `C:\Users\khanj\jarvis_home` or `C:\Users\khanj\Downloads`. Those are legacy 2025 prototypes. The real system is **`F:\JARVIS2.0`**.
2. **Context Runaway**: Keep sessions compact and focused on discrete deliverables.
3. **No Hallucinated Methods**: Bind strictly to names exported in `src/jarvis/supervisor/__init__.py`.

---

## 4. Current Task & Next Steps

1. **Check Status**:
   ```bash
   cd F:\JARVIS2.0
   uv run python scripts/supervisor.py status
   ```
2. **Select Next Milestone**:
   - Determine next milestone per `docs/ORCHESTRATOR_ARCHITECTURE.md` (e.g., M3.2 or next mission runtime expansion).
3. **Run Verification**:
   - For any package, verify using:
     ```bash
     uv run python scripts/supervisor.py verify <PACKAGE>
     ```

---

## 5. Non-Negotiable Operating Rules

* **Rule 1**: Do NOT touch `src/jarvis/kernel/`. All work is additive in `src/jarvis/supervisor/`, `scripts/`, or `tests/supervisor/`.
* **Rule 2**: Do NOT merge to `main` or push to `origin`. Those are creator-gated (L2).
* **Rule 3**: Always run `uv run pytest -q` to verify zero regressions across the 548 existing tests.
