# M6 — Living Deployment (Kickoff & Architectural Roadmap)

**Status:** ACCEPTED DESIGN — architectural contract for implementation.  
**Author/owner:** Antigravity (Gemini) designs & verifies; Big Pickle (OpenCode) implements.  
**Milestone:** Phase 5: Milestone M6 (Living Deployment / Always-On Persistence).  
**Baseline:** `task/supervisor @ 304eb22`, **860 passed in 256s**, 0 failed.  
**Proof Target (M6):** `always-on daemon -> wake-word trigger -> background mission scheduler -> encrypted tunnel -> automated backup/DR`.

---

## 1. Why This Exists

With Milestones M0 through M5 verified and frozen, JARVIS has:
1. A tamper-evident, append-only event-sourced deterministic memory kernel (M1, M2).
2. A multi-step mission execution orchestrator with dynamic worker bridges, automated failure recovery, and daemon lease tracking (M3).
3. Local multimodal perception across Whisper STT, Piper TTS, vision adapters, and a real-time turn-taking FSM (M4).
4. Embodiment infrastructure: HTN planner, external node protocol, event replication, peripheral control, and physical safety plane (M5).

However, JARVIS currently only runs upon explicit CLI invocation (`jarvis mission`, `jarvis voice`).
To transition into a **living, persistent cognitive companion** per `docs/MASTER_BUILD_SPEC.md:5075-5088`:
- JARVIS must run continuously as an **Always-On Living Daemon** capable of graceful restarts, signal handling, and health reporting.
- Perception must be hands-free via a **Low-Power Wake-Word Detection Seam**.
- Companion nodes (e.g. mobile phones) must securely communicate over an **Encrypted Tunnel Seam** (mTLS / authenticated cryptographic session).
- Missions must execute autonomously in the background via a deterministic **Autonomous Mission Scheduler**.
- The entire memory ledger and projection state must be protected by **Automated Backup, Disaster Recovery (DR) & Self-Healing**.

---

## 2. Specification Grounding (Master Build Spec §5075-5088)

- **Always-on node**: Background daemon supervising system loop with signal trap and health checks.
- **Phone body & Voice**: Companion presence and streaming voice integration.
- **Low-power perception**: Wake-word detector seam triggering voice turns hands-free.
- **Secure remote access**: End-to-end authenticated, encrypted node tunneling.
- **Background missions**: Autonomous recurring / scheduled mission execution.
- **Backup & Disaster Recovery (DR)**: Automated SQLite online backup, verification exports, and integrity restoration.
- **Self-healing operations**: Crash recovery, state reconstruction, and WAL reconciliation.
- **Cross-device continuity**: Synchronization across workstation and external bodies.

---

## 3. Work Packages for Milestone M6

| Package | Title | Deliverables | Tests |
|:---|:---|:---|:---|
| **M6.1** | **Always-On Living Daemon & Lifecycle** | `src/jarvis/deployment/daemon.py` | `tests/deployment/test_daemon.py` |
| **M6.2** | **Low-Power Perception & Wake-Word Seam** | `src/jarvis/deployment/wakeword.py` | `tests/deployment/test_wakeword.py` |
| **M6.3** | **Secure Remote Access & Encrypted Tunnel** | `src/jarvis/deployment/tunnel.py` | `tests/deployment/test_tunnel.py` |
| **M6.4** | **Background Missions & Autonomous Scheduler** | `src/jarvis/deployment/scheduler.py` | `tests/deployment/test_scheduler.py` |
| **M6.5** | **Automated Backup, Disaster Recovery & Healing** | `src/jarvis/deployment/backup.py` | `tests/deployment/test_backup.py` |

---

## 4. Acceptance Invariants

1. **Deterministic Replay Guarantee**: Any restored backup or replicated stream verifies hash chain integrity and reproduces identical memory digests.
2. **Fail-Closed Security**: Unauthenticated tunnel connections or mismatched cryptographic keys are refused immediately.
3. **Graceful Teardown**: Daemon shutdowns must safely flush open SQLite WAL journals, release peripherals, and persist state within ≤2.0 seconds.
4. **Zero Regressions**: All 860 existing tests must remain green across all milestones.
