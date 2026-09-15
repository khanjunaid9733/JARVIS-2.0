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

---

## ADR-005: EventLog Physical Schema (SQLite WAL, Hash-Chained, Append-Only)

* **Status:** `ACCEPTED`
* **Date:** 2026-09-14
* **Context:**
  Spec §85 defined the event log conceptually but not physically. The EventLog is the kernel's memory of reality; changing it mid-M1 moves everything downstream. Mechanical integrity was also unproven: no hash-chain fields existed anywhere in the spec.
* **Decision:**
  One SQLite WAL table `events`, append-only (mutation-rejecting triggers), replay order = global sequence:
  `seq INTEGER PRIMARY KEY` · `event_id TEXT UNIQUE (ULID)` · `stream_id TEXT` · `stream_seq INTEGER` · `ts_utc TEXT` (injected Clock, UTC ISO-8601) · `event_type TEXT` · `schema_version INTEGER` · `principal_id TEXT` · `mission_id TEXT NULL` · `task_id TEXT NULL` · `cause_event_id TEXT NULL` · `correlation_id TEXT NULL` · `payload_json TEXT` (canonical: UTF-8, sorted keys, no insignificant whitespace) · `payload_sha256` (of canonical payload) · `prev_event_sha256` (chain) · `actor_model TEXT NULL`.
  Indexes: `(stream_id, stream_seq) UNIQUE`, `event_type`, `mission_id`.
* **Consequences:**
  - §85 integrity requirement becomes mechanically testable: tampered row → `payload_sha256`/`prev_event_sha256` mismatch → replay halts with typed failure (NAT-04).
  - Deterministic replay is enforced by canonical payload serialization + injected Clock.
  - Physical schema is frozen for M1; migration requires creator-approved evidence per the amendment rule.

---

## ADR-006: Structured Output Mechanism for M1 — Pydantic v2 Validation First

* **Status:** `ACCEPTED`
* **Date:** 2026-09-14
* **Context:**
  §131.12 left the SCHEMA_CONSTRAINED mechanism as "native OR Outlines OR Instructor" — an undecided seam OpenCode cannot build against. The M1 baseline already mandates Pydantic v2.
* **Decision:**
  M1 = Pydantic v2 schema validation with retry-on-validation-failure; Ollama's native JSON-schema format is used behind the identical call when available. Outlines and other constrained-decoding backends remain future Model Gateway adapters. Frozen M1 interface: `generate_structured(role_contract, schema) -> ValidatedOutput | TypedFailure`.
* **Consequences:**
  - Zero new dependencies for M1; the seam stays intact (§131.12 unchanged architecturally).
  - Structured-output replacement later requires no kernel change — only a new adapter behind the same interface.

---

## ADR-007: Creator Keypair, M1 Scope — Ed25519, Fail-Closed

* **Status:** `ACCEPTED`
* **Date:** 2026-09-14
* **Context:**
  The Creator keypair is the registry trust anchor (ADR-003), but no algorithm, storage, or failure behavior was defined. M1 needs a small, explicit implementation — not enterprise PKI.
* **Decision:**
  - Algorithm: Ed25519 via the `cryptography` package.
  - Storage: `~/.jarvis/keys/creator.ed25519`, 0600, no passphrase in development (accepted M1 risk, recorded).
  - Fingerprint: first 8 hex of SHA-256(public key) — emitted as the pairing code in the §127.1 smoke test.
  - M1 signing scope: authority events (`capability.provider_added` / `provider_promoted` / `provider_deprecated` / `provider_revoked`) and creator approvals; detached signature stored on the event.
  - Unavailable key: **fail closed** — typed `authority.unavailable` failure; authority-requiring operations are rejected, never bypassed.
  - Rotation/recovery in M1: manual regenerate + re-registration events; no escrow.
* **Consequences:**
  - "Creator signed approval" becomes a verifiable mechanism, not a noun.
  - Key loss is recoverable by manual re-registration; the log records authority continuity explicitly.

---

## ADR-008: Windows-Native Development Host for M1, with Portability Rules

* **Status:** `ACCEPTED`
* **Date:** 2026-09-14
* **Context:**
  The development machine is Windows; the spec's later deployment baseline assumes Linux/systemd/Docker. Left undecided, OpenCode bakes in environment assumptions that become painful later. Machine evidence: PATH `python` = 3.11.9, `uv python find` = 3.14.5 (outside the contract window), 3.12.6/3.13.x also installed.
* **Decision:**
  M1 develops Windows-native (Python 3.12, uv, pytest, Ollama native, SQLite WAL all viable). Portability rules from day one: `pathlib` everywhere, `JARVIS_HOME` env override for the state directory, no POSIX-only assumptions, no OS-specific service code. WSL2 exists only as an M0-audit fallback row. systemd/Docker remains post-M1 per existing spec. Python is pinned by `requires-python = ">=3.12,<3.14"` in `pyproject.toml` so uv cannot silently select 3.14.
* **Consequences:**
  - The M0 audit's Python row is satisfied by explicit pinning, not interpreter roulette.
  - Linux deployment later requires no kernel rewrite.

---

## ADR-009: Negative Acceptance Tests Bound to the M1 Gate

* **Status:** `ACCEPTED`
* **Date:** 2026-09-14
* **Context:**
  §127.1's smoke test is happy-path only. The kernel constitution's invariants deserve adversarial proof.
* **Decision:**
  Five negative acceptance tests (NAT-01…05, full table in spec §134.3) are binding for M1 completion: ungranted capability → `intent.rejected` (constitution 6/11); non-creator `provider_added` rejected (5); byte-identical replay (20); tampered row halts replay with typed failure (10); ungated completion refused (12).
* **Consequences:**
  - M1 is not complete if the smoke test passes but any NAT fails.
  - Each NAT is a named pytest target in the M1 test suite, traceable to a constitution clause.
