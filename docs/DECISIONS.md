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

---

## ADR-010: M1 Model Backend and Routing — Groq OpenAI-Compatible Endpoint; LiteLLM Deferred

* **Status:** `ACCEPTED`
* **Date:** 2026-09-18
* **Context:**
  The M0 audit's open setup item reads "configure model backend (install Ollama
  or select remote OpenAI-compatible endpoint)" — either path was permitted.
  Spec §131.11 nevertheless names LiteLLM as "the *routing implementation*
  behind the Model Gateway interface" for M1, and ADR-006 references Ollama's
  native JSON-schema format "when available." Module 6 shipped a JARVIS-owned
  OpenAI-compatible adapter (`src/jarvis/providers/openai_compatible.py`) bound
  to Groq, with no LiteLLM dependency. The deviation was disclosed in the
  adapter docstring but not recorded as a decision, so an ACCEPTED decision
  (§131.11) was left diverged by code.
* **Decision:**
  1. The M1 model backend is a **remote OpenAI-compatible endpoint (Groq)**,
     selected under the M0 audit's explicit "remote OpenAI-compatible endpoint"
     option. This is a permitted choice, not a deviation.
  2. The gateway continues to own what §131.11 assigns it: routing policy
     declaration, budget enforcement, capability metadata, provenance
     recording, failover semantics, model lifecycle events. Provider API
     translation and key handling remain inside the JARVIS-owned adapter.
  3. **LiteLLM is deferred** as the routing *implementation* behind the
     `ProviderAdapter` seam. M1 has exactly one model route
     (`model.generate_structured` → `model.adapter`), so a third-party router
     would add a dependency for no routing benefit and would place a
     non-JARVIS component inside the substitution seam before multi-provider
     routing exists. When a second model provider, cross-provider failover, or
     provider-agnostic key handling is required, LiteLLM is introduced **as an
     adapter implementation behind the unchanged `ProviderAdapter` Protocol**,
     per §131.11's own "Revisit at M3" trigger. No kernel change is required
     for that swap (ADR-001).
* **Consequences:**
  - The §131.11 divergence is closed: recorded, with the deferral bounded to a
    named trigger (multi-provider routing / failover), not left open-ended.
  - No code change. `openai_compatible.py` remains a conforming adapter; the
    kernel imports no provider client (ADR-001 intact).
  - ADR-006's "Ollama native JSON-schema when available" clause is noted as
    not exercised in M1; the Pydantic-v2-validation-with-retry mechanism it
    mandates is the active path, unchanged.
  - If the creator later prefers the Ollama path, only the adapter and the
    `model.adapter` binding change; the gateway, registry, and intent ABI are
    unaffected.

---

## ADR-011: Governed Skill Execution Seam

* **Status:** `ACCEPTED`
* **Date:** 2026-09-27
* **Context:**
  The skill runtime was built for a library of hand-written skills, then
  pointed at a 2,400-entry library that is mostly documentation. Five concrete
  failures, each reproduced by command before anything was changed:

  1. **Audit events never existed.** `EventLog.append` has the signature
     `append(event: Event | Mapping)`. Ten call sites invoked it as
     `append(stream_id=..., event_type=..., ...)`, which raises `TypeError`, and
     each wrapped the call in `except Exception: pass`. `skill.learned`,
     `automation.created`, `dialogue_turn`, `agent.tool_executed`,
     `memory_saved`, and the four UI action events were therefore all silently
     dropped. `jarvis do "learn: …"` reported success and produced a file with
     no ledger entry.
  2. **Untagged fences were treated as shell.** `_extract_code_blocks` defaulted
     an untagged ``` fence to `bash`, and `SkillWorkflowStep.language` defaulted
     to `"bash"`. `jarvis skill run 3d-games` fed that skill's own Markdown
     numbered list to `sh` and reported `1.: command not found`, exit 127.
  3. **Every skill inherited the operator's secrets.** `_run_step` built the
     child environment with `env = dict(os.environ)`, so any dispatched skill
     could read `JARVIS_MODEL_API_KEY` and anything else exported in the session.
  4. **No execution admission.** All 2,400 skills were dispatchable; a natural
     language goal could resolve to documentation and run it.
  5. **Containment was misdescribed.** The module docstring claimed "strict path
     jailing" while the step ran under a bare `subprocess.run` with no
     process-tree cleanup, so a grandchild survived a timeout. Nothing enforced
     a filesystem boundary at any point.

* **Decision:**
  Five stages, each defaulting to deny:

  * **S0 — Audit helper.** `EventLog.audit(*, stream_id, event_type,
    principal_id, payload, mission_id)` constructs the `Event` and returns its
    id. All ten kwargs-style call sites converted and all ten
    `except Exception: pass` blocks removed; those callers now propagate, so an
    unaccountable operation fails. An AST regression test over `src/jarvis`
    fails the build if any kwargs-style `.append()` reappears.
    *Not uniform, deliberately:* the skill dispatcher's per-step `_emit` still
    catches, because a locked or full log must not make the whole library
    unusable. That failure was invisible (counted in telemetry, returned on a
    result field nobody read); it is now logged and printed by `jarvis skill
    run`, so a missing ledger record is visible rather than silent.
  * **S1 — Parse-time admission.** An untagged fence parses as `text` and is
    inert. `EXECUTABLE_LANGUAGES` is the admission set; `SkillWorkflowStep
    .is_executable` requires both an admitted language and non-empty code.
    Unknown tags (`rust`, …) are preserved for inspection and never executed.
    `CACHE_VERSION` is bumped to 2, because the on-disk cache fingerprints only
    source files: without a bump, v1 caches kept serving the old `bash` typing
    and `3d-games` still ran prose.
  * **S2 — Learning is a file write, not a capability.** *(Revised. See
    "Revision" below.)* `learn_skill` writes `.agents/skills/<id>/SKILL.md` and
    journals `skill.learned` with the payload's `code_sha256`. It does not
    require a signed grant, and the result states plainly that the skill is
    **not executable yet**, naming `jarvis skill admit <id>` as the next step.
    No grant file, `grant` subcommand, or `CreatorActionType.SKILL_LEARN` remains.
  * **S3 — Default-deny environment.** `build_skill_env` copies only
    `INHERITED_ENV_ALLOWLIST` (shell resolution, temp paths, locale) plus proxy
    prefixes, forces `PYTHONUTF8=1`, and applies `env_overrides` last. Secrets
    are withheld unless a caller passes one deliberately.
  * **S4 — Default-deny execution.** `skills/admission.py` holds the allowlist;
    `SkillDispatcher` refuses any unlisted skill with a journalled
    `skill.refused` (`refusal_stage: "admission"`) before a subprocess exists.
    Seeded with the two reviewed, hand-written hashing skills; `jarvis skill
    admit <id>` and `jarvis skill admitted` manage it. Discovery is unaffected —
    every skill stays listable, searchable and inspectable. A dry run is exempt,
    since it creates no subprocess and is how an operator decides what to admit.
  * **S4b — Content pin.** `jarvis skill admit` records a sha256 of the reviewed
    `SKILL.md`. That pin is now *enforced*: if the file changes after review,
    the skill is refused (`refusal_stage: "admission_content_pin"`) before any
    subprocess. It was previously write-only, which left admission revocable
    the instant it was granted, since the agent can rewrite any file on disk.
  * **S5 — Honest containment.** Steps run through the existing
    `ContainedProcess` seam (kill-on-close Job Object on Windows, process group
    on POSIX, whole-tree termination on timeout) rather than a bare
    `subprocess.run`. `CONTAINMENT_BOUNDARY` states plainly that this is process
    containment and NOT a filesystem, network, or registry jail; the false
    "strict path jailing" claim is removed.

* **Consequences:**
  - The skill seam is now default-deny at four independent points: language
    admission, execution allowlist, environment inheritance, and audit
    write-through.
  - `learn_skill` succeeds and is journalled, and its reply says the skill is
    not executable until admitted. The cost of writing code to disk is paid at
    the execution allowlist (S4), not at the file write.
  - Running an unadmitted library skill now fails loudly
    (`REFUSED: … not on the execution allowlist`) instead of running its
    documentation. Admitting the ~1,800 library skills that carry real code is
    a deliberate, reviewable act, not a default.
  - `ContainedProcess` gained an optional `env` argument, defaulting to `None`
    (inherit) so every existing caller is unchanged. Skill dispatch is its
    first consumer to pass an explicit environment.
  - Not addressed here, still true: the external OpenCode worker produces no
    artifact on this machine (exit 0, empty output, killed at 200–300s), and
    `create_automation` writes JSON that `AutonomousScheduler` never reads.
    Both are recorded rather than claimed fixed.
  - A filesystem/network jail for skill steps is **not** provided. If that is
    required, it is a separate decision about an OS-level sandbox, not an
    extension of the process containment above.

* **Revision (S2, after implementation):** The creator-authority gate on
  `learn_skill` was **withdrawn as unsound** and replaced. It was verified
  bypassable, not merely suspected to be:

  - The agent holds `filesystem_operation`, which writes any path. It can create
    `.agents/skills/<n>/SKILL.md` directly and never reach `learn_skill`.
  - The agent holds `run_system_command`, so it can shell out to the grant
    minting command, which signs with the creator key in its own
    `$JARVIS_HOME`. This was reproduced end to end: a self-minted grant was
    accepted and the skill was written.

  A signature over a payload the subject can produce at will is not an
  authorization. The gate's payload binding was real, but its *provenance*
  claim was false, and the digest ceremony bought nothing the system could
  enforce. Presenting it as a security control was the error.

  The replacement states the actual power structure: **learning is a file write;
  the execution allowlist (S4) is the capability boundary.** S4 is evaluated at
  dispatch against the file, not against how it arrived, so it holds for skills
  written by `learn_skill`, by `filesystem_operation`, or by hand. This was
  verified directly — a skill written straight to disk by a tool is refused at
  execution until admitted.

  What S2 still does: refuses empty code, journals `skill.learned` with the
  payload digest, and never claims a written skill is runnable. The digest is
  retained as an audit artifact identifying *what* landed, not as proof of
  *who* wrote it.
