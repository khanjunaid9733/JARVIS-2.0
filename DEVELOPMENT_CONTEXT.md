# JARVIS 2.0 — DEVELOPMENT CONTEXT (DEVELOPMENT_CONTEXT.md)

**Date**: 2026-09-14  
**Current Milestone**: `PRE_M0` (Repository Establishment & Context Foundation)  
**Implementation Status**: `NOT_STARTED` (Zero runtime code exists)  
**Current Objective**: Establish shared development context, organize documentation, and prepare for M0 audit.

---

## 1. WHAT ARE WE BUILDING?

We are building **J.A.R.V.I.S.**, a persistent, personal cognitive operating system for its Creator.

JARVIS is not merely a chatbot, coding agent, voice assistant, or collection of API calls. It is an enduring, general-purpose cognitive and execution system designed to maintain **one continuous identity** across:
* Development PC and workstation
* Mobile / phone body
* Internet, web services, and cloud
* Files, software, and development tools
* Voice, vision, and multimodal perception
* Multiple underlying AI models
* Dynamic multi-agent societies
* Physical robotics, ROS2, and digital-twin simulations

> [!IMPORTANT]
> **The Model is an Accelerator Inside JARVIS. The Model is NOT JARVIS Itself.**
> Individual AI models (DeepSeek, Claude, GPT, Llama, Gemini) can and will be swapped. JARVIS's persistent identity, memories, goals, permissions, and event history remain continuous regardless of which model is currently serving an inference request.

---

## 2. WHY? (THE COGNITIVE VISION)

Human cognition maintains an integrated world model, episodic and semantic memory, a self-model, attention, metacognition, and goal pursuit across time and environments. Current AI tools are ephemeral: sessions close, context windows reset, and models execute actions without persistent accountability or true world-state awareness.

JARVIS is built to bridge this chasm. It will feature:
* **Persistent Identity & Memory**: An append-only event-sourced ledger where state is rebuildable and auditable.
* **Autonomous Agency with Deterministic Governance**: Autonomous planning guided by hard security boundaries that prevent runaway hallucination.
* **Embodiment Flexibility**: Moving seamlessly from text terminal to hands-free voice on mobile to ROS2 robotic control.

---

## 3. WHAT IS THE CURRENT REALITY?

| Dimension | Real State on Disk |
| :--- | :--- |
| **Milestone** | `PRE_M0` |
| **Runtime Code** | **Zero lines**. No Python package, no daemon, no CLI runtime yet. |
| **Database / EventLog** | **Non-existent**. `~/.jarvis/log.db` has not been created yet. |
| **Capabilities / Tools** | **Not implemented**. No capability registry or adapters exist yet. |
| **Agents / Capsules** | **Not implemented**. |
| **Specification State** | Architecture specifications are established and frozen for M1 planning. |

If you are an AI reading this: **Do NOT hallucinate that JARVIS is already running or that any modules exist in `src/`.**

---

## 4. WHAT HAS BEEN FORMALLY ACCEPTED?

The following architectural invariants are **ACCEPTED** and non-negotiable (see `docs/DECISIONS.md`):

1. **Event-Sourced Deterministic Kernel**:
   * All state is derived from an append-only event log.
   * Projections (memory, world state, missions, active agents) are rebuildable via deterministic replay.
2. **The Model Proposes, Determinism Disposes**:
   * Models propose intents, manifest contracts, and summaries.
   * Deterministic code validates syntax, enforces capability constraints, commits transactions, and verifies outcomes.
   * Models cannot grant themselves capabilities, bypass safety, or declare their own completion.
3. **External Capability Substitution Seam**:
   * No JARVIS kernel code may directly import an external provider (e.g., LiteLLM, vLLM, Browser Use, Qdrant).
   * External capabilities sit strictly behind versioned contracts, adapters, and registry-controlled bindings.
   * External providers execute outside the canonical kernel process.
4. **Creator Authority Boundary**:
   * The root trust anchor is the Creator keypair.
   * Only the Creator may register, promote, or revoke capability providers.
   * Agents may propose providers, but cannot self-register or self-grant privileges.
5. **Capability Contracts are Lower Bounds**:
   * A contract declares minimum guarantees. Substitution succeeds only when all guarantees and caller constraints are met.
   * Degraded substitutions must be recorded explicitly in provenance; silent degradation is forbidden.

---

## 5. WHAT IS MERELY PROPOSED / EXPERIMENTAL?

The following concepts have been discussed in exploratory analysis (e.g., DeepSeek v2 notes), but are **NOT** part of the M1 build scope:
* Spiking Neural Networks (SNN) / neuromorphic hardware
* Confidential Computing / Hardware TEE integration
* Market-based token/compute economy for multi-agent negotiation
* Dynamic graph-theoretic agent topology learning
* Heavyweight distributed brokers (Kafka, Kubernetes, NATS JetStream)
* Vector databases as canonical memory (Qdrant is strictly an index seam for later, not canonical memory)

These remain in the `PROPOSAL` / `RESEARCH` category and must not be implemented until empirical need and formal Creator approval exist.

---

## 6. WHAT IS STRICTLY FORBIDDEN?

* ❌ **Direct Provider Imports**: Never `import litellm`, `import vllm`, or `import browser_use` directly into kernel core.
* ❌ **Implicit Privilege Escalation**: Never allow an agent to bypass capability checks or grant itself permissions.
* ❌ **Unverified Completion**: Never treat a model's statement ("Task is done") as evidence of task completion. Completion requires deterministic verification.
* ❌ **Architecture Creep**: Never introduce new architectural subsystems, message buses, or databases during M1.
* ❌ **Silent History Mutation**: The event log is strictly append-only. Never mutate past events.

---

## 7. CURRENT ROADMAP & NEXT IMMEDIATE STEPS

```text
[PRE-M0: Context Foundation]  <-- WE ARE HERE
            ↓
[M0: Environment Audit]        <-- Next: Audit Python, uv, SQLite, Git, Models -> docs/M0_AUDIT.md
            ↓
[M1: Cognitive Kernel]         <-- EventLog (SQLite WAL), Intent ABI, Registry, Local Model Adapter
            ↓
[M2: Memory OS]                <-- Typed memory, PII seam, retrieval projections
            ↓
[M3: Mission Runtime]          <-- Sagas, effect recovery, agent capsules, browser/doc adapters
            ↓
[M4+: Multimodal & Society]    <-- Phone node, voice, vision, multi-agent coordination
            ↓
[M5+: Physical Embodiment]     <-- ROS2, Gazebo, hardware emergency-stop
```

### Immediate Action Plan
1. Establish the repository context files (`AGENTS.md`, `DEVELOPMENT_CONTEXT.md`, `project_state.yaml`, `README.md`).
2. Move specifications into `docs/` (`docs/MASTER_BUILD_SPEC.md`, `docs/DECISIONS.md`, `docs/GLOSSARY.md`).
3. Run Git initialization and create the baseline commit.
4. Execute the formal M0 audit and generate `docs/M0_AUDIT.md`.
