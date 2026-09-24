# M5 — Embodiment & External Device Nodes — Kickoff

**Status:** PROPOSAL — scope drafted for creator ratification; implementation not started.  
**Author/owner:** Big Pickle (OpenCode) implements; Freebuff attacks; Antigravity verifies.  
**Milestone:** Phase 4: Milestone M5 (Embodiment & External Device Nodes / Cognitive Expansion).  
**Baseline:** `task/supervisor @ 1fcfdf4`, **814 passed in 261.61s**, 0 failed.  
**Proof Target (M5):** `decomposed goal -> node dispatch -> peripheral effect -> e-stop/verify -> event log sync`.  

---

## 1. Why This Exists

With Milestones M0 through M4 verified and frozen, JARVIS possesses:
1. A tamper-evident, append-only event-sourced deterministic memory kernel (M1, M2).
2. A multi-step mission execution orchestrator with dynamic worker bridges, automated failure recovery, and daemon lease tracking (M3).
3. Local multimodal perception across Whisper STT, Piper TTS, vision adapters, and a real-time turn-taking FSM (M4).
4. An end-to-end runnable composition root and live execution loop (`src/jarvis/live.py` and `src/jarvis/live_dispatch.py`).

However, JARVIS currently exists strictly inside a single workstation process boundary. To fulfill the foundational cognitive vision articulated in [`DEVELOPMENT_CONTEXT.md`](file:///F:/JARVIS2.0/DEVELOPMENT_CONTEXT.md) and [`docs/MASTER_BUILD_SPEC.md`](file:///F:/JARVIS2.0/docs/MASTER_BUILD_SPEC.md):
- JARVIS must maintain **one continuous identity** across workstation, phone body, IoT nodes, and physical peripherals.
- Task planning must graduate from static linear decomposition (`_LocalDecomposer`) to dynamic, goal-driven **Hierarchical Task Networks (HTN)**.
- Actuation in the physical/external world requires a deterministic **Physical Safety Plane** and hard hardware/software **Emergency Stop (E-Stop)**.
- Events originating on external nodes must synchronize back to the canonical ledger without history mutation or distributed split-brain.

---

## 2. Specification Grounding (Master Build Spec & Decisions)

Anchored in `docs/MASTER_BUILD_SPEC.md` and `REMAINING_WORK.md`:
* **§M5 Cognitive Expansion (`MASTER_BUILD_SPEC.md:5058-5074`)**: Advanced planner, HTN methods, attention, metacognition, self-model, adaptive routing, skill acquisition, continuous compliance.
* **§M6 Living Deployment (`MASTER_BUILD_SPEC.md:5075-5088`)**: Always-on node, phone body, low-power perception, secure remote access, background missions, cross-device continuity.
* **§M7 Embodiment (`MASTER_BUILD_SPEC.md:5089-5101`)**: Robot body, peripheral adapters, physical safety plane, real-time controller integration, embodied mission verification.
* **Invariant I5 & External Capability Substitution Seam**: External nodes and hardware drivers sit behind versioned `ProviderAdapter` contracts; no direct vendor drivers inside the deterministic kernel.
* **NAT-01 / NAT-02 / NAT-05 Discipline**: All physical side effects must execute through the two-phase `EffectEnvelopeEngine` (prepare -> authorize -> commit -> verify) and require Creator cryptographic authority.

---

## 3. Proposed M5 Work Packages

Each package is additive, hermetic, and tested before promotion:

| # | Package | Scope & Responsibilities | Deliverables |
|---|:---|:---|:---|
| **M5.1** | **HTN Planner & Dynamic Task Decomposition** | Replace linear `_LocalDecomposer` with a deterministic Hierarchical Task Network planner. Decomposes high-level goals into domain methods and primitive operators with declared preconditions, resource locks, and postcondition effects (integrates with `manifest_dag.py`). | `src/jarvis/kernel/planner/htn.py`<br>`tests/kernel/test_htn_planner.py` |
| **M5.2** | **External Node Protocol & Lightweight RPC Seam** | Define versioned `NodeSpec`, node capability manifests, pairing code verification (expanding `new_pairing_code` in `bootstrap.py`), and a lightweight RPC wire protocol (JSON-RPC over secure WebSocket/HTTP/BLE) behind a `ProviderAdapter`. | `src/jarvis/nodes/protocol.py`<br>`src/jarvis/nodes/rpc_adapter.py`<br>`tests/nodes/test_node_rpc.py` |
| **M5.3** | **Distributed Event Log Replication & Sync** | Peer/hub event synchronization mechanism. Propagates append-only hash-chained event logs between workstation and external nodes. Enforces causal ordering via vector clocks and cryptographic hash validation without silent history mutation (Invariant I6). | `src/jarvis/kernel/sync/replication.py`<br>`tests/kernel/test_log_sync.py` |
| **M5.4** | **Peripheral Control & IoT Capability Contracts** | Standardized capability contracts for external hardware (`peripheral.gpio`, `peripheral.sensor`, `peripheral.serial`, `camera.capture`). Path-jailed and port-jailed execution governed by `EffectEnvelopeEngine`. | `src/jarvis/adapters/peripherals/`<br>`tests/adapters/test_peripherals.py` |
| **M5.5** | **Physical Safety Plane & Hardware E-Stop** | Deterministic fail-closed safety monitor. Features software/hardware E-Stop latch (absorbing `HALT`), watchdog heartbeat timers (fail-closed release), velocity/power ceiling invariants, and human-in-the-loop actuation gating. | `src/jarvis/safety/estop.py`<br>`src/jarvis/safety/watchdog.py`<br>`tests/safety/test_estop.py` |

---

## 4. Scope Boundaries (Strict Exclusions for M5)

To maintain focus and avoid architectural bloat:
1. ❌ **No Heavy Distributed Brokers**: Never introduce Kafka, Redis, or NATS JetStream. Sync relies strictly on the SQLite hash-chained event store.
2. ❌ **No ROS2 / Heavy Simulation in M5.1–M5.4**: Full ROS2/Gazebo integration is reserved for M7. M5 builds the abstract node and peripheral capability seams.
3. ❌ **No Direct Device Binding in Core Kernel**: Device drivers must remain in adapter modules or out-of-process node agents.
4. ❌ **No Unauthenticated Node Pairing**: Nodes cannot self-join without explicit Creator cryptographic attestation.

---

## 5. Non-Negotiable Acceptance Invariants

1. **Deterministic Replay Across Nodes**: Replaying a replicated event stream on any node yields the exact same `MemoryProjection.digest()` as the source node.
2. **E-Stop Precedence**: An emergency-stop signal supersedes all ongoing missions, aborts pending dispatches, and releases actuator holds within ≤50ms.
3. **Fail-Closed Disconnection**: A lost heartbeat between the orchestrator and a node immediately halts running effects on that node (`HOLD` state).
4. **All 814 Existing Tests Must Remain Green**: Zero regressions across M1–M4.

---

## 6. Implementation Sequencing & Next Immediate Step

1. **Creator Ratification**: Creator reviews and formally ratifies this M5 Kickoff scope.
2. **Package M5.1 Kickoff**: Open `docs/M5_1_KICKOFF.md` detailing the HTN planner contract, data models, and test probes.
3. **Execution Division**:
   - **Big Pickle (OpenCode)**: Implements M5.1 HTN planner.
   - **Freebuff (DeepSeek)**: Attacks the planner with cyclic graphs, unsolvable method trees, and race conditions.
   - **Antigravity (Gemini)**: Verifies determinism, invariant compliance, and test coverage.
