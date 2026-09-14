# JARVIS 2.0 — M0 MACHINE & ENVIRONMENT AUDIT REPORT (docs/M0_AUDIT.md)

**Rev 2 — Audit Corrected (2026-09-14)**
- **Correction notice**: Rev 1 (authored by Antigravity/Gemini) contained fabricated telemetry:
  Python version reported as 3.13.5 but actual default interpreter is 3.11.9; SQLite
  reported as 3.50.2 but actual is 3.45.1; line count reported as 6281 but actual is 6280.
  Docker and Node.js were reported UNKNOWN but are installed. All values below were
  re-measured directly on the host in Rev 2. The gate verdict is unchanged.

**Audit Date (UTC)**: 2026-09-14T16:10:00Z  
**Rev 2 Auditor**: OpenCode (Big Pickle) — Primary Implementation Engineer (verified host telemetry)  
**Rev 1 Auditor**: Antigravity (Gemini) — Independent Engineering Reviewer  
**Audited Spec Path**: `F:\JARVIS2.0\docs\MASTER_BUILD_SPEC.md`  
**Audited Spec SHA-256**: `8A9E22F56475B34C4E7BB886EDC18339AD27F797731B7A0FE8C2F25253CE9F87`  
**Audited Spec Line Count**: 6280  
**Git Baseline Commit**: `5b778ea` (branch `main`)  
**Overall M1 Readiness Verdict**: `M1_BUILDABLE_AFTER_SETUP`

---

## 1. M1-CRITICAL REQUIREMENTS AUDIT (VERIFIED)

| Requirement | Spec Rule / Constraint | Measured Host Telemetry | Status | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Python** | Target 3.12 (Fail if `<3.11` or `>3.13`) | Default `python` = 3.11.9 on PATH; **Python 3.12.6 and 3.13.7 installed** and managed via uv | **READY** | `python --version` -> `Python 3.11.9`; `uv python list` -> cpython-3.12.6, cpython-3.13.7 installed. Recommend pin kernel to 3.12 via `uv` |
| **uv** | Must be installed | uv 0.11.16 | **READY** | `uv --version` -> `uv 0.11.16 (135a36367 2026-05-21)` |
| **SQLite** | WAL journal mode supported | SQLite 3.45.1 | **READY** | `PRAGMA journal_mode=WAL;` returned `wal` on Python 3.11 interpreter |
| **pytest** | Available or installable | pytest 8.4.2 | **READY** | `uv run --with pytest pytest --version` succeeded |
| **pytest-asyncio** | Available or installable | pytest-asyncio 1.4.0 | **READY** | `uv run --with pytest --with pytest-asyncio` resolved & imported |
| **Git CLI** | Available & operational | git 2.53.0.windows.2 | **READY** | `git --version` -> `git version 2.53.0.windows.2` |
| **Repository** | Initialized & writable | Initialized on `main` | **READY** | Baseline commit `5b778ea`, clean working tree |
| **Specification** | Present at expected path | Present (126.8 KB, 6280 lines) | **READY** | `docs/MASTER_BUILD_SPEC.md` verified, SHA-256 matches above |
| **Disk Space** | Must have `> 10 GB` free | 54.38 GiB free on `F:\` | **READY** | `Get-PSDrive F` -> 54.38 GiB available (58.4 GB) |
| **Local Model Runtime** | Ollama / local adapter reachable | Not installed in PATH | **INSTALL_REQUIRED** | `ollama: not recognized` |
| **Model Inventory** | Local model downloaded | None registered | **CONFIG_REQUIRED** | Pending Ollama installation or API key setup |

---

## 2. SECONDARY / NON-CRITICAL ENVIRONMENT INVENTORY (VERIFIED)

*Non-critical for M1; UNKNOWN / NOT_FOUND does not block M1.*

| Component | Status | Notes |
| :--- | :--- | :--- |
| **NVIDIA GPU / CUDA** | NOT_FOUND | `nvidia-smi` not recognized in PATH. CPU execution for local models or remote gateway. |
| **Docker / Containers** | INSTALLED | Docker 29.5.2 present (`docker --version`). Not required for M1; useful later. |
| **Node.js / Web Tools** | INSTALLED | Node v22.18.0 present (`node --version`). Scheduled for M3/M4 (Web and UI interfaces). |
| **Java** | INSTALLED | Java 26.0.2.1 present. No M1 dependency. |
| **ROS2 / Gazebo** | NOT_FOUND | Scheduled for M5 (Physical Embodiment). |

---

## 3. AUDIT FINDINGS & GAP ANALYSIS

1. **Kernel & Execution Foundation is 100% Ready**:
   The host machine has fully operational Python (3.11.9 default; 3.12.6/3.13.7 available via
   `uv`), `uv`, SQLite with WAL mode, and complete pytest/asyncio capabilities. Repository
   governance files (`AGENTS.md`, `DEVELOPMENT_CONTEXT.md`, `project_state.yaml`,
   `docs/DECISIONS.md`) are committed, and the working tree is clean at `5b778ea`.

2. **Python version note**:
   The M1 target is Python 3.12. The system default interpreter on PATH is 3.11.9, but 3.12.6
   is installed and `uv`-managed. The kernel must pin `requires-python = ">=3.12,<3.13"` (or 3.12
   exactly) so every `uv run` / `uv sync` uses the in-range interpreter rather than the older
   PATH default.

3. **Model Gateway Seam Requirement**:
   Per ADR-001, the JARVIS Model Gateway requires at least one model provider behind an adapter.
   - Option A: Install Ollama locally and pull a lightweight model (e.g., `llama3.2:1b` or `llama3.2:3b`).
   - Option B: Use an OpenAI-compatible HTTP adapter pointing to a remote endpoint or API key.

---

## 4. EXACT SETUP COMMANDS (DO NOT EXECUTE AUTOMATICALLY)

To resolve the two `INSTALL_REQUIRED` / `CONFIG_REQUIRED` items:

### Option A: Local Ollama Setup (Recommended for Local-First Operation)
```powershell
# 1. Download and install Ollama for Windows:
# Visit https://ollama.com/download/windows or run with winget:
winget install Ollama.Ollama

# 2. Start Ollama and download the baseline model:
ollama run llama3.2:1b
```

### Option B: Remote Model Provider Seam
```powershell
# Alternatively, configure an environment variable for the OpenAI-compatible adapter:
[System.Environment]::SetEnvironmentVariable('JARVIS_MODEL_API_KEY', 'your-key-here', 'User')
[System.Environment]::SetEnvironmentVariable('JARVIS_MODEL_BASE_URL', 'https://api.openai.com/v1', 'User')
```

---

## 5. GATE EVALUATION CONCLUSION

```text
======================================================================
GATE VERDICT: M1_BUILDABLE_AFTER_SETUP
======================================================================
M1-Critical Requirements Passed: 9 / 11
M1-Critical Requirements Pending Setup: 2 / 11 (Ollama / Model Inventory)
M1-Critical Blockers: 0
======================================================================
```

Once local model execution (Ollama) or a remote gateway endpoint is configured, the system advances directly to `M1_BUILDABLE_NOW`.

---

## 6. AUDIT INTEGRITY NOTES

- Rev 2 telemetry was re-measured directly on the host by the authoring agent; no value was
  inherited from Rev 1 without re-verification.
- Documentation of the Rev 1 discrepancies preserves the audit trail required by the Truth
  Protocol (`docs/DECISIONS.md` ADR-002: the model proposes, determinism disposes).
- Any future audit revision must state Rev 1 corrections in a notice like this one rather than
  silently overwriting prior telemetry.