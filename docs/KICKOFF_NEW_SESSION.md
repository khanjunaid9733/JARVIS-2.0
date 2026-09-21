# KICKOFF CONTEXT: NEW AGENT SESSION

> **Purpose:** Provide immediate, high-signal ground truth for any fresh OpenCode (Big Pickle) or agent session starting on `task/supervisor`. Read this document first before inspecting files.

---

## 1. Machine-Verified Ground Truth

| Datum | Verified Reality | Status |
|---|---|---|
| **Directory** | `F:\JARVIS2.0` (NEVER use `C:\Users\khanj\jarvis_home`) | ACTIVE WORKSPACE |
| **Branch** | `task/supervisor` @ `31d7a55` | ACTIVE |
| **Main Baseline** | `main` @ `afa6beb` (M2.4 merged) | FROZEN |
| **Baseline Commit** | `7607a6f1f226824b5a7038e15efd66932529da7c` | IMMUTABLE |
| **Core Kernel** | `src/jarvis/kernel/**` byte-identical to `main` | UNTOUCHED (0 diffs) |
| **Test Suite** | **721 passed in 39.51s**, 0 failed | 100% GREEN |
| **Active Plan** | M2 Residuals / Memory & Capability Hardening | IN PROGRESS |
| **State Directory** | `F:\JARVIS_ORCHESTRATOR_STATE\` | INITIALIZED & ACTIVE |
| **Frozen Packages** | `["M3.1", "M3.2", "M3.3", "M3.4", "M3.5", "M2.5", "M2.6", "M2.7"]` (signed in `evidence/`) | ACCEPTED |

---

## 2. What Is Already Implemented & Verified

### A. The Supervisor Package (`src/jarvis/supervisor/`)
All 6 contract modules + `__init__.py` exist and export 30 symbols (pinned by `tests/supervisor/test_api_contract.py`):
1. **`authority.py`**: `AuthorityTier` (L0, L1, L2), `EscalationReason` (9 reasons), `decide_authority_tier(reason)`, `is_creator_gated(reason)`. Pure data, deterministic lookup.
2. **`evidence.py`**: `EvidenceSource` (7 rungs), `EvidencePrecedence` (`FILESYSTEM=7` down to `AGENT_MEMORY=1`), `Evidence`, `EvidenceLedger` (`with_entry`, `highest`, `authority`, `conflicts`), `VerificationResult`.
3. **`lifecycle.py`**: `LifecycleState` (9 states), `LifecycleEvent` (14 events), `TaskLifecycle` FSM, `lifecycle_transitions` table. `FROZEN_SUCCESS` is absorbing; only creator-gated `REOPEN` moves it.
4. **`mutation_guard.py`**: `PackageSnapshot` (`folder_fingerprint`), `MutationReport` (`mutated`, `added`, `removed`, `changed`), `MutationGuard` (`seal`, `check`).
5. **`recovery.py`**: `RecoveryAction` (`NONE`, `RETRY`, `RESTART`, `ROLLBACK`, `ESCALATE`, `HOLD`), `RecoveryPolicy`, `RecoveryPlan`, `decide_recovery(...)`. Pure data ladder fold.
6. **`supervisor.py`**: `Verifier`, `Observer`, `Acceptor` protocols; `SupervisorDecision`; `Supervisor` (`decide`, `verify`, `freeze`).

### B. Unit & Integration Tests (`tests/supervisor/`, `tests/orchestrator/`, `tests/review/`, `tests/kernel/`, `tests/effects/`)
All suites passing (721 tests total):
* `tests/supervisor/`: 9 test files (121 tests)
* `tests/orchestrator/`: 5 test files (98 tests: `mission_runner` 16, `bridges` 20, `router` 15, `recovery_engine` 12, `daemon` 35)
* `tests/review/`: 5 review probe files (94 probes, including Freebuff's M3.3 and M2.7 probes)
* `tests/kernel/`: 19 test files (347 tests, including M2.5 `test_privacy.py` 18 tests, M2.7 `test_manifest_dag.py` 19 tests)
* `tests/effects/`: 1 test file (10 tests: `test_filesystem.py`)
* Plus: `tests/` root (21), `tests/acceptance/` (15), `tests/providers/` (15)

### C. Verification & Orchestration Scripts (`scripts/`)
* **`scripts/verify.py`**: Phase 1 L0 Verification Authority. Enforces pytest suite, compares frozen baseline against commit `7607a6f`, executes review probes, collects authority fingerprint, and emits canonical SHA-256 digested JSON evidence.
* **`scripts/journal.py`**: Append-only, hash-chained, fsync-durable JSONL journal (`journal.jsonl`).
* **`scripts/supervisor.py`**: CLI orchestrator (`init`, `status`, `verify`) enforcing single-writer lock (`supervisor.lock`), durable ledger (`ledger.json`), and coordinates verify + journal emission.

### D. Milestones M3.1–M3.5, M2.5, M2.6 & M2.7 Verified & Frozen
* Evidence bundles:
  - `F:\JARVIS_ORCHESTRATOR_STATE\evidence\M3.1.json` (`sha256:82234d7554342760aaaea6d496e911de7980550bfc9e719f0b051316a4c0d057`)
  - `F:\JARVIS_ORCHESTRATOR_STATE\evidence\M3.2.json` (`sha256:c2349f8f3acaca67965a4943d35157f15faaec5c2dfa88d0fd033c537446fe63`)
  - `F:\JARVIS_ORCHESTRATOR_STATE\evidence\M3.3.json` (`sha256:51634863eeeb4c82ce94c5892e72f51ca0a1ae303b58635015def77ede55c603`)
  - `F:\JARVIS_ORCHESTRATOR_STATE\evidence\M3.4.json` (`sha256:bdf8ec16a4c1ee78ed55bc391d6ec9eaf062ae3a53be14e5375b3b04ed3a22a5`)
  - `F:\JARVIS_ORCHESTRATOR_STATE\evidence\M3.5.json` (`sha256:8430008e2c0eae2b4ba7f063b5b70673a754721b1cac7ab295e946c3914c906e`)
  - `F:\JARVIS_ORCHESTRATOR_STATE\evidence\M2.5.json` (`sha256:dabeb4de8edff01611a0be90b25fc443566c5bc3fecd7b4681a0c510fcf6c1e4`)
  - `F:\JARVIS_ORCHESTRATOR_STATE\evidence\M2.6.json` (`sha256:d61561b58f23062257d6d20170445825be365601d4600f2fa7813d1aea6f6cb5`)
  - `F:\JARVIS_ORCHESTRATOR_STATE\evidence\M2.7.json` (`sha256:79a2be3e13ce3b065f29b6afa5ec4ceec0fa200a66d9ccb21e416b177201d412`)
* Ledger updated: `frozen_packages: ["M3.1", "M3.2", "M3.3", "M3.4", "M3.5", "M2.5", "M2.6", "M2.7"]`, `current_milestone: "M2.7"`, `last_known_good: "31d7a555c3cc9771beaf6d1fbaac354b8d4a4f2d"`, `last_verify_exit: 0`.

---

## 3. Critical Context on Past Failures (Do Not Repeat)

1. **WRONG DIRECTORY**: NEVER look for or edit files in `C:\Users\khanj\jarvis_home` or `C:\Users\khanj\Downloads`. Those are legacy 2025 prototypes. The real system is **`F:\JARVIS2.0`**.
2. **Context Runaway**: Keep sessions compact and focused on discrete deliverables.
3. **No Hallucinated Methods**: Bind strictly to names exported in `src/jarvis/supervisor/__init__.py`.

---

## 4. Current Task & Next Steps

1. **Next milestone**: M3.5 is FROZEN. The next focus per `docs/ORCHESTRATOR_ARCHITECTURE.md` is the next M3 expansion (e.g., wire the daemon's decision plane to the live `leases/` watcher + `Effects` seam as a real background process, or begin M4 Multimodal).
2. **Run Verification**:
   - For any package, verify using:
     ```bash
     uv run python scripts/supervisor.py verify <PACKAGE>
     ```
3. **Verify history (do not re-run blindly)**: `journal.jsonl` seq 8 records a REJECT (M3.5 suite flake, `F-M3.3-FB-2` process-tree race) that was fixed by commit `15c4fe9` and followed by seq 9 ACCEPT. A package already accepted in evidence/ should not be re-verified unless its code changes.

---

## 5. Non-Negotiable Operating Rules

* **Rule 1**: Do NOT touch `src/jarvis/kernel/`. All work is additive in `src/jarvis/supervisor/`, `src/jarvis/orchestrator/`, `scripts/`, or `tests/`.
* **Rule 2**: Do NOT merge to `main` or push to `origin`. Those are creator-gated (L2).
* **Rule 3**: Always run `uv run pytest -q` to verify zero regressions across the 664 existing tests.
* **Rule 4**: Commit BEFORE running `supervisor.py verify <pkg>` - evidence must be `verify_py_source: git_blob`, never `working_tree`.
