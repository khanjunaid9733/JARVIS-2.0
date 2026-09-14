# JARVIS 2.0 — CANONICAL GLOSSARY (docs/GLOSSARY.md)

This glossary establishes standard terminology for JARVIS 2.0 across all engineering agents, specifications, and codebases.

---

### Core Architectural Terms

* **Cognitive Kernel**: The authoritative, deterministic core of JARVIS. Owns the event log, processes state transitions, enforces policy, authorizes capabilities, and manages agent lifecycles.
* **Event Log**: The append-only, immutable database of record (`~/.jarvis/log.db`). Stores all state changes as typed, causal events.
* **Projection**: A rebuildable, read-optimized view of state computed purely by replaying the event log (e.g., active missions, memory index, agent roster, world model).
* **Deterministic Replay**: The process of rebuilding all system projections and current state from the genesis event, guaranteeing bit-exact state recovery.

---

### Security, Intent & Capability Boundaries

* **Intent**: A high-level, structured representation of what a user or agent seeks to achieve.
* **Intent ABI**: The formal boundary that receives, validates, and routes structured intents before any manifest is synthesized.
* **Manifest**: A frozen, hashed, declarative execution contract detailing required capabilities, resource budgets, scopes, and isolation parameters for an action or agent.
* **Capability Contract**: A versioned semantic interface declaring the minimum guarantees (lower bounds) required to perform a category of effects (e.g., `fs.read.v1`, `browser.navigate.v1`).
* **Capability Registry**: An event-sourced projection that tracks registered capability providers, their versions, health, adapters, and trust levels.
* **Provider Adapter**: A JARVIS-owned translation layer that bridges a generic JARVIS capability contract to a specific external tool, library, CLI, or API.
* **Agent Capsule**: An isolated execution sandbox that encapsulates an agent with its specific manifest, granted capabilities, resource limits, and filesystem/network scopes.
* **Creator Principal**: The ultimate human authority and root trust anchor, identified cryptographically by the Creator keypair.

---

### Execution & Observability

* **Effect**: A concrete, observable external operation (e.g., writing a file, making an HTTP request, moving a robotic arm).
* **Saga / Effect Transaction**: The multi-step protocol for high-risk or irreversible effects: `PREPARE → AUTHORIZE → COMMIT → VERIFY → RECONCILE`.
* **Provenance**: The unbroken causal lineage linking an external effect back through its manifest, contract, model inference, and triggering intent/event.
* **Model Gateway**: The intermediary service that routes model requests to appropriate backends (local Ollama, vLLM, remote APIs) while enforcing budgets, timeouts, and structured output schemas.
* **Always-On Node**: The persistent server or primary workstation host that maintains JARVIS's operational identity and event log when satellite devices (like mobile phones) are disconnected.

---

### Truth Protocol Levels

* **`VISION`**: Long-term directional goals and aspirational milestones.
* **`PROPOSAL`**: Research, design explorations, or suggested additions not yet formally approved.
* **`ACCEPTED_DESIGN`**: Approved architectural decisions documented in ADRs and the Master Specification.
* **`IMPLEMENTED`**: Real, committed code in `src/` intended to satisfy an accepted design.
* **`VERIFIED`**: Implemented code supported by passing unit tests, property checks, and empirical evidence.
