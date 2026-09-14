# JARVIS 2.0 — ARCHITECTURE DECISION RECORDS (docs/DECISIONS.md)

This file documents all **ACCEPTED ARCHITECTURAL INVARIANTS** for JARVIS 2.0.  
These decisions are binding across all platforms and engineering agents. Changes to accepted decisions require creator approval based on empirical implementation evidence.

---

## ADR-001: External Capability Substitution Seam

* **Status:** `ACCEPTED / ARCHITECTURE INVARIANT`
* **Date:** 2026-09-14
* **Context:**
  JARVIS requires extensive external capabilities: model serving, web browsing, document parsing, computer control, speech/audio, vision, and robotics. If JARVIS code directly imports third-party packages, external dependencies pollute the kernel, making upgrades, sandboxing, and security boundaries impossible to maintain.

* **Decision:**
  All external tools, services, model-serving backends, and capability providers are accessed strictly through versioned semantic contracts.
  **No JARVIS kernel code may directly import an external provider.**
  Provider-specific behavior is isolated behind JARVIS-owned adapters and registry-controlled bindings.

* **Required Pattern:**
  ```text
  JARVIS CODE
      ↓
  CAPABILITY CONTRACT
      ↓
  CAPABILITY REGISTRY
      ↓
  JARVIS-OWNED PROVIDER ADAPTER
      ↓
  EXTERNAL PROVIDER (Process / Service / CLI)
  ```
  The same substitution pattern applies to models:
  ```text
  MODEL ROLE CONTRACT
      ↓
  MODEL REGISTRY
      ↓
  MODEL ADAPTER
      ↓
  MODEL PROVIDER / SERVING BACKEND
  ```

* **Consequences:**
  - External providers remain 100% hot-swappable without touching core cognitive logic.
  - Supply-chain metadata, licensing, and security audits are centralized.
  - Failures map into a canonical typed failure taxonomy.
  - Every provider executes outside the canonical kernel process.
  - Example: `Browser Use` and `Playwright` can substitute for each other behind the `browser.*` contract.
  - Example: `LiteLLM` is an adapter component behind the Model Gateway, not the owner of JARVIS routing policy.

---

## ADR-002: Manifest Synthesis is Model-Proposed, Determinism-Disposed

* **Status:** `ACCEPTED / ARCHITECTURE INVARIANT`
* **Date:** 2026-09-14
* **Context:**
  Allowing probabilistic LLMs to directly invoke tools, allocate permissions, or execute arbitrary effects causes privilege escalation, prompt injection vulnerabilities, and non-deterministic behavior.

* **Decision:**
  Intents compile into execution manifests through a **model-proposed, deterministically-validated** pipeline.
  The model proposes semantic capability contracts; it **never** selects providers, **never** grants capabilities, and **never** bypasses validation.

* **Pipeline:**
  ```text
  INTENT
    ↓
  CONTRACT PROPOSAL       ← schema-constrained model proposal
    ↓
  STATIC VALIDATION       ← deterministic (schema, DAG, undeclared check)
    ↓
  POLICY VIABILITY        ← deterministic (budgets, autonomy levels, permissions)
    ↓
  MANIFEST                ← frozen, hashed, and logged
    ↓
  CAPABILITY RESOLUTION   ← registry lookup, never model
  ```

* **Consequences:**
  - Manifest synthesis is completely deterministic, replayable, and testable.
  - Model hallucination or injection during synthesis produces `intent.rejected`, not unauthorized effects.

---

## ADR-003: Provider Registration Requires Creator Authority

* **Status:** `ACCEPTED / ARCHITECTURE INVARIANT`
* **Date:** 2026-09-14
* **Context:**
  If autonomous agents could dynamically download, install, and register new tools or providers without creator intervention, a compromised agent could register malicious backdoors.

* **Decision:**
  Only the Creator principal may emit `capability.provider_added`, `capability.provider_promoted`, or `capability.provider_revoked`.
  Agents may formulate proposals for new providers, but no principal or agent may self-register or self-grant.

* **Consequences:**
  - The registry's ultimate trust anchor is the Creator keypair.
  - An agent cannot expand its own capability set or grant itself elevated permissions.

---

## ADR-004: Capability Contracts are Lower Bounds, Not Equivalences

* **Status:** `ACCEPTED / ARCHITECTURE INVARIANT`
* **Date:** 2026-09-14
* **Context:**
  Different provider implementations of the same capability (e.g., local Ollama vs. remote GPT-4o, or headless Chromium vs. full browser) exhibit differing behaviors, latencies, and limitations.

* **Decision:**
  A capability contract specifies **minimum guarantees** (lower bounds). Provider adapters declare their specific behavioral profiles.
  Substitution is valid only when the provider meets the contract's lower bound and satisfies all strict requirements of the caller.
  Degraded substitution must be recorded explicitly in provenance; silent downgrades are forbidden.

* **Consequences:**
  - Provider replacement is transparent and auditable.
  - Callers can declare strict invariants (e.g., `requires_local_execution: true`, `max_latency_ms: 500`).
