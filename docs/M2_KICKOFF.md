# M2 — Memory OS (+ First Tool Body) — Kickoff

**Status:** PROPOSAL — scope drafted for ratification; not started.
**Author/owner:** Big Pickle (OpenCode) implements; Freebuff attacks; Antigravity verifies.
**Precedent seams:** every M1/M1.1 module — pure deterministic folds over the
integrity-verified log (`MemoryProjection`, `MissionLifecycleOwner`,
`BudgetLedger`), typed failure paths (`TypedFailure`), additive optional
seams instead of behavior changes, and the `ModelGateway`/`ProviderAdapter`
substitution seam for Model Fabric roles.

## 1. Why this exists

Spec §133 and §M2 define M2 as the **Memory OS**; §134.1 STRETCH also
leaves one unbuilt item (manifest-DAG validation) that belongs to M2's
intent-compilation package. The M1.1 sign-off (`docs/M1_1_SIGNOFF.md`)
carries forward explicit M2 handoffs:

- key-based authority (NAT-02 second half) — the "M2 key-based module"
- token accounting (adapter `usage` seam) — M2 budgets/rate limits
- manifest-DAG validation → intent-to-manifest compilation
- first real capability adapter + filesystem effect (M2 "First Tool Body")

## 2. M2 scope (spec-anchored)

From `MASTER_BUILD_SPEC.md`:

- **§M2 `## M2 — Memory + First Tool Body` (4957-4980):** episodic traces,
  memory API, consolidation pipeline, memory verification, filesystem
  effect, sandbox, intent-to-manifest compilation, compiled work orders,
  loop breaker, budgets/rate limits. **Proof:** `read file → evidence →
  memory trace → restart → recover`.
- **§133 ladder (6252-6258):** Memory OS + PII detection seam + embedding
  seam + retrieval seam + memory verification + semantic checkpoints.
- **§84.3 (3242-3264):** two-tier consolidation — episodic trace →
  cheap search/index → consolidation → extract → verify → contradiction
  resolution → promote → semantic/procedural memory. *«Not every
  interaction becomes durable semantic memory.»*
- **§84.4 (3266-3278):** memory verification proportional to impact —
  cheap deterministic checks → semantic verifier → independent verifier for
  high-impact memory. Memory classes carry provenance/confidence/source/
  timestamp/validity/retention/supersession.
- **§131.14 (5968-5978):** Memory OS may use replaceable providers for
  embeddings / reranking / PII detection — **Model Fabric roles, not Memory
  OS identity**. PII-check before durable promotion per policy.
- **§86.1 (3351-3363):** semantic checkpoint triggers feed the `recover`
  half of the proof.

## 3. Proposed work packages (ratify before implementing)

Mirrors module-14 style: each package is a standalone module behind the
existing seams, deterministic, additive-only to frozen modules 1–17.

| # | Package | Kernel home (proposal) | Notes |
| - | :--- | :--- | :--- |
| M2.1 | **Memory API + episodic trace** — `memory.retrieve`/`memory.trace` semantics; episodic trace as first-class events folded into a new `MemoryIndex` projection | `src/jarvis/kernel/memory_api.py` + projection | working/episodic stores §6.3; proof step "read file → evidence → memory trace" |
| M2.2 | **Embedding + retrieval seams** — §131.14 roles bound behind `ModelGateway`/`ProviderResolver`; no index dependency in the kernel (Qdrant et al. stay OUT per §134.1 EXCLUDED) | `ModelGateway` consumer | embeddings/reranking are adapter-provided like `model.generate_structured` |
| M2.3 | **Consolidation pipeline** — §84.3 two-tier: extract → verify → contradiction resolution → promote; decisioning is DATA, not hardcoded branches | `src/jarvis/kernel/memory_consolidate.py` | "Not every interaction becomes durable memory" |
| M2.4 | **Memory verification** — §84.4 severity ladder; provenance/confidence/validity/supersession fields on `memory.write.*` | extends module 10/`memory_write.py` path (additive) | cheap deterministic checks first |
| M2.5 | **PII detection seam** — §131.14/§5978; policy-gated redaction/tagging before durable promotion | policy adapter role | fail-closed on policy privacy class (module 9 precedent) |
| M2.6 | **Filesystem effect + sandbox** — first real capability adapter behind `ProviderAdapter` + `EffectEnvelopeEngine` (NAT-01 discipline; `mission_id` stamped per F-M14-1) | `src/jarvis/adapters/fs.py` | "First Tool Body"; M2 proof starts here |
| M2.7 | **Intent-to-manifest compilation + compiled work orders + manifest-DAG validation** — closes the unbuilt §134.1 STRETCH item | extends module 3/intent ABI (additive) | DAG checks are a pure validator |
| M2.8 | **Key-based authority** — NAT-02 second half; Ed25519 signature verification for provider/creator authorization | `src/jarvis/kernel/authority_keys.py` | unblocks `creator_principal_id` equality trust model |
| M2.9 | **Budgets/rate limits + loop breaker** — consume module 16 ledger + `tokens` seam; mission capsule §80.4 limits enforced on the gateway call path | `src/jarvis/kernel/gate_limits.py` | first adapter to report `usage` lands M2 budgets honestly |
| M2.10 | **Semantic checkpoints + recovery** — §86.1 triggers; snapshot metadata; M2 proof: restart → recover | `src/jarvis/kernel/checkpoint.py` | closes the proof chain |

Scope boundaries (do NOT build in M2):
- No mission scheduler, no sagas/compensation execution, no agent runtime
  (module 14 declared the `CompensationRecord` seam; real compensators are M3
  per §83).
- No external vector index/DB; retrieval stays in-kernel or behind the
  provider seam (§134.1 EXCLUDED).
- No phone/voice/vision/robotics bodies.

## 4. Entry conditions (gates)

1. M1 + M1.1 signed off — **DONE 2026-09-18** (`docs/M1_1_SIGNOFF.md`).
2. Modules 1–17 frozen; M2 work is additive-only behind ratified designs.
3. `main` in sync with `origin/main` — **DONE** (`160a3c2`).
4. Each work package opens with its own kickoff/ratification doc before
   touching `src/`.

## 5. Sequencing

1. Ratify the package list + ordering (creator)
2. M2.1 memory API/episodic trace: design + kickoff doc
3. Implement package-by-package with adversarial + independent passes
   (module-14/15-17 pattern)
4. M2 proof (`read file → evidence → memory trace → restart → recover`)
   as the milestone acceptance transcript

---

## Paste-ready kickoff prompt (M2.1 — memory API + episodic trace)

```markdown
# M2.1 — Memory API + episodic trace store — kickoff

You are Big Pickle (OpenCode), primary implementation engineer.
Baseline: `main @ HEAD`, 292 passed, modules 1-17 FROZEN + creator-signed.

READ FIRST (re-derive from disk, trust nothing quoted):
- docs/MASTER_BUILD_SPEC.md §6.3 (memory kinds), §84.3/§84.4, §131.14, §127.1,
  §133 M2 ladder
- src/jarvis/kernel/memory_projection.py (pure-fold precedent)
- src/jarvis/kernel/memory_write.py + memory_query.py (current write/read path)
- src/jarvis/kernel/event_log.py (Event schema: streams, mission_id, causal discipline)
- project_state.yaml (m1_1_stretch, nats, m2_memory_os)

DELIVER:
1. Ratify or refine the M2.1 contract (episodic trace shape, memory API surface,
   projection/digest, retrieval ordering) BEFORE writing kernel code.
2. Implement the kernel module + tests. Additive-only; modules 1-17 behavior
   unchanged; no new dependencies; deterministic folds (no clock/RNG/network).
3. Wire the CLI minimally (retrieve/recover proof stub) only if the API shape
   requires it — orchestration stays outside the kernel.
4. Determinism tests: replay twice -> identical state + digest.

Do not build: external indexes, model providers, PII pipeline, filesystem
effects, budgets enforcement (their own packages). No history rewrites. No push.
```