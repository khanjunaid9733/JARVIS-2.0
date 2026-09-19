# M2.2 — Embedding + Retrieval Seams (Kickoff & Design Contract)

**Status:** PROPOSAL — contract to ratify before any `src/` change.
**Author/owner:** Big Pickle (OpenCode) implements; Freebuff attacks; Antigravity verifies.
**Milestone:** M2 (Memory OS), package M2.2 (of `docs/M2_KICKOFF.md`).
**Baseline:** `main @ 838d182`, **332 passed**; modules 1–17 FROZEN + creator-signed;
M2.1 merged (`m2_1_completed`).
**Carried-in ruling (creator, 2026-09-19):** FB-1 recall tier/verification distinction
is DEFERRED TO M2.2 — this package delivers it. FB-2 digest decision does not touch this
package (retrieval reads `MemoryIndex` state only).

## 1. Why this exists

Spec §133 M2 ladder lists **embedding seam + retrieval seam**; §131.14
(5968-5978) requires they be **replaceable Model Fabric providers — Memory OS
roles, not Memory OS identity** — with embedding/rerank adapters bound behind
the existing `ModelGateway`/`ProviderResolver` substitution seam, exactly like
`model.generate_structured` (module 6). Per §134.1, no external vector index/DB
may enter the kernel (Qdrant et al. EXCLUDED); the kernel must work
deterministically with no model provider at all (M1.1/§127.1 precedent).

M2.2 delivers the retrieval plane that M2.3 consolidation and the M2 proof
(`read file → evidence → memory trace → restart → recover`) read from — and
closes the accepted FB-1 gap by carrying each hit's **tier** (`memory` vs
`trace`) and **verified** flag through retrieval.

## 2. Grounding in the frozen code (re-derived, not assumed)

- **module 6** `ModelGateway.generate_structured(role_contract, schema, ..., input_text)`
  (M1.1 additive seam) is the ONLY routed role; `RoleContract` already DECLARES
  `EMBED = "embed"` and `RERANK = "rerank"` (§131.13) but `M1_ROLE_CONTRACTS`
  binds only `SCHEMA_CONSTRAINED`. Route data lives at `model_gateway.py:96-99`.
- **module 4/registry** `ProviderAdapter` protocol (invoke/health_check),
  `resolve_provider`/`resolve_version_for_provider` (F3), `ContractDef` with
  mandatory `args_schema`, first-registered-wins resolution. Providers are
  data, never hardcoded by the gateway.
- **M2.1** `MemoryIndex` (memories + traces folds, NAT-03 state digest, replay-verified)
  and `Memory` facade: `recall()` = module-11 lexical union semantics,
  `(-score, event_id)` total order. `_CombinedView` shim feeds module-11's
  retriever. Log/env 312+20 = 332.
- **module 11** `recall()` token overlap scoring; `ANSWER_MIN_CONFIDENCE`.

Constraints: no frozen module behavior change; additive-only, versioned seams;
no clock/RNG/network in the kernel; offline path byte-deterministic (Hermetic
D2 precedent: bogus backend must never be dialled by the offline path).

## 3. Design contract (to be ratified)

```text
A) Role binding (additive, versioned, module 6 untouched)
   ModelGateway.generate_structured gains ONE additive kwarg:
       role_contracts: dict[RoleContract, tuple[str, str]] | None = None
   - None (default) -> current M1_ROLE_CONTRACTS routing; every frozen caller
     stays byte-identical (same pattern/guarantee as the M1.1 input_text seam).
   - When provided, route lookup = {**M1_ROLE_CONTRACTS, **role_contracts}.
   M2.2 route DATA lives in the new module, never in model_gateway.py:
   M2_ROLE_CONTRACTS = {
       RoleContract.EMBED:  ("memory.embed",  "^1.0"),
       RoleContract.RERANK: ("memory.rerank", "^1.0"),
   }

B) New kernel module src/jarvis/kernel/memory_retrieval.py (deterministic core)
   - RankedMemory (pydantic frozen, extra="forbid"):
       event_id: str
       content: str
       source: str
       score: float
       tier: Literal["memory", "trace"]     # which fold the hit came from
       verified: bool                        # True iff from the memory.write
                                             # committed fold (gate-passed, §84.4
                                             # tier separation; a trace is a raw
                                             # caller-declared record)
   - retrieve(combined: Mapping[str, dict], query: str, *, limit, ranker=None)
       -> list[RankedMemory]
       Candidate funnel = M2.1 lexical union (module-11 semantics) + tier tags
       from which map each event_id came from (memories vs traces).
       ORDER (deterministic total order):
           (-score, tier_order, event_id)
       where tier_order = 0 for memory, 1 for trace (equal-score verified
       memories outrank raw traces — the FB-1 discriminator, data rule in the
       module, not branching).
       `limit` validated (non-positive/non-int -> ValueError, M2.1 C4 rule).
       Empty/non-match -> [].
   - RetrievalRanker protocol (the §131.14 provider seam):
       async def rerank(self, query: str, candidates: list[RankedMemory],
                        limit: int) -> list[RankedMemory]
       - Model-backed implementation `ModelRetrievalRanker` (gateway + route
         DATA, resolved via M2_ROLE_CONTRACTS[RERANK]): schema-validated
         scores; on TypedFailure/transport/validation failure -> FALL BACK to
         deterministic lexical order (never raises; offline byte-identical).
       - NoOp/default ranker -> candidates unchanged (pure lexical path).
   - Embedding seam (declared, optional, NOT consumed by default ordering):
       async def embed(self, texts: list[str]) -> list[list[float]]
       provider-bound like rerank; used by M2.3 consolidation / future
       sim-score. No kernel dependency on it; no vector store.

C) Facade (additive)
   Memory.retrieve(query, *, limit=3, ranker=None) -> list[RankedMemory]
     delegates to module B.retrieve over the SAME combined view as recall().
   Memory.recall() REMAINS UNTOUCHED (M2.1 facade bit-identical; existing
   21 M2.1 tests + 20 probes keep passing verbatim).

D) Model rerank audit (evidence for M2.9 ledger)
   When a model rerank actually RUNS (bound provider + successful response),
   append ONE audit event "memory.retrieve.reranked" on stream "memory"
   (payload: provider_id, contract_id/version, candidate_event_ids, limit).
   Does NOT enter MemoryIndex folds (memories/traces predicates unchanged;
   digest inputs unchanged). No rerank -> no event (offline logs unchanged).

E) CLI: NO new surface in M2.2. `jarvis recall` stays exactly as M2.1 (contract
   E unchanged). The rerank seam is exercised by tests/M2.3+, not by a new flag.

Determinism targets (mirror NAT-03/G20):
   same log + no ranker -> same RankedMemory order/digest across rebuilds;
   same log + ModelRetrievalRanker with a stub adapter -> deterministic given
   stub; real provider results are NOT cross-run digest promises (network).

Scope boundaries (do NOT build):
   - no vector index / external DB / FAISS / embeddings persistence (M2.2 only
     exposes the role seam; storage/consumers are M2.3+)
   - no consolidation/extraction/contradiction (M2.3)
   - no verification ladder changes (M2.4), no PII (M2.5), no budget
     enforcement (M2.9), no checkpoint/recovery (M2.10)
```

## 4. Entry conditions (gates)

1. M2.1 completed + merged — **DONE** (`902392a`/`838d182`, 332 passed).
2. Modules 1–17 frozen; additive-only behind ratified design — **in force**.
3. This contract ratified (accept or refine A–E) — **PENDING**.
4. `main` in sync with `origin/main` — **DONE** (`838d182`).

## 5. Sequencing

1. Ratify items A–E (creator) — including whether M2.2 also binds an embed
   contract now or only declares the seam (default: declare seam + route DATA,
   no provider registration in M2.2 — the Groq-adapter embed/rerank binding is
   M2.9/budget-package or a creator decision).
2. Implement `memory_retrieval.py` + additive `role_contracts` kwarg + facade
   `Memory.retrieve` + audit event + tests (Big Pickle) on task/m2.2.
3. Adversarial pass (Freebuff) on routing/ordering/fallback/audit seams.
4. Independent verify (Antigravity).
5. Merge to `main` when green; update `project_state.yaml`.

---

## Paste-ready kickoff prompt (implementer)

```markdown
# M2.2 — Embedding + retrieval seams — kickoff

You are Big Pickle (OpenCode), primary implementation engineer.
Baseline: `main @ HEAD`, 332 passed; modules 1-17 FROZEN + creator-signed;
M2.1 merged (memory_trace/index/api + CLI recall).

READ FIRST (re-derive from disk, trust nothing quoted):
- docs/M2_KICKOFF.md (M2 scope, proof)
- docs/M2_2_KICKOFF.md §3 (ratified contract items A-E)
- docs/MASTER_BUILD_SPEC.md §131.14 (Model Fabric roles), §84.3/§84.4
- src/jarvis/kernel/model_gateway.py (generate_structured, M1_ROLE_CONTRACTS,
  input_text additive precedent, TypedFailure)
- src/jarvis/kernel/registry.py (ProviderAdapter, ContractDef, resolver methods)
- src/jarvis/kernel/memory_api.py + memory_index.py + memory_query.py (M2.1)
- docs/M2_1_RECONCILIATION.md §3 (FB-1 ruling -> tier/verified lands HERE)
- project_state.yaml (m2_memory_os status truth protocol)

DELIVER:
1. Re-verify the ratified contract against frozen code. Changes to A-E -> say
   what/why in the implementation note before coding.
2. Implement src/jarvis/kernel/memory_retrieval.py + the additive
   `role_contracts` kwarg on ModelGateway.generate_structured (None default,
   byte-identical frozen callers) + Memory.retrieve additive method +
   memory.retrieve.reranked audit event (only on REAL rerank) + tests.
   Task branch task/m2.2; merge only when green.
3. offline byte-identical: no ranker -> retrieve() == lexical order == M2.1
   candidates + tier/verified tags; bogus backend never dialled (test it).
4. Deterministic total order (-score, tier_order, event_id); limit validation.
5. No new CLI. No new dependencies. Modules 1-17 behavior unchanged.

Do not build: vector stores, consolidation, verification ladder, PII, budget
enforcement, checkpoints (their packages). No history rewrites. No push.
```