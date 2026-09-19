# Freebuff — Adversarial Review Report (M2.2)

## Milestone 2 · Package M2.2 — Embedding + Retrieval Seams

**Reviewer:** Freebuff (adversarial red-team; JARVIS 2.0)
**Target:** branch `task/m2.2` @ **`8f788c5`** (`feat(kernel): M2.2 embedding + retrieval seams`)
**Date:** 2026-09-19
**Status of findings:** **PROPOSALS** — not accepted architecture. **No `src/` file was modified.**
**Baseline:** 348 passed · **with evidence probes: 384 passed** (36 probes added, all PASS).
**Verdict:** **M2_2_RECONCILIATION_REQUIRED** — two HIGH findings sit directly on the package's
reason-for-being (the FB-1 verified-vs-trace discriminator and "schema-validated scores"), and the audit
seam has a silently-skipping default path plus a digest-drift side effect the ratified contract says the
package must not have.

---

## 1. Preconditions (reproduced, not trusted)

| Check | Observed |
| :--- | :--- |
| Branch / HEAD | `task/m2.2` @ `8f788c5` (`M2.2: embedding + retrieval seams…`) |
| Working tree | clean (report + probes added afterwards; `src/` untouched) |
| Baseline suite | `348 passed in 19.40s` — matches prompt |
| Probes | `tests/review/test_freebuff_redteam_m2_2.py` — **36 passed in 4.09s** |
| Full suite w/ probes | `384 passed in 21.82s` (**+36** vs baseline) |
| Additive-first | probe run confirmed frozen module-6 behavior byte-identical; `M1_ROLE_CONTRACTS` untouched |
| Offline hermiticity | confirmed no dial / no clock / no ULID on the `ranker=None` path (probe A1) |

---

## 2. Findings

### FB-M2.2-1 — HIGH — Non-finite scores (NaN/±inf) pass "schema-validated" rerank and get audited
**Location:** `src/jarvis/kernel/memory_retrieval.py:113-119` (`RerankScores.scores: list[float]`) consumed at
`:171-193` (`ModelRetrievalRanker.rerank`).
**Failure mode:** pydantic v2 lax `float` accepts `NaN`, `+inf`, `-inf` (verified live). A model emitting
`[nan, 0.5]` is treated as a **success**: the pass is reranked (no fallback to the deterministic lexical order),
`NaN` is spliced into `RankedMemory.score` (poisoning any consumer arithmetic and the rank key), and the
`memory.retrieve.reranked` audit event FIRES — attesting a real model rerank on garbage. The contract's
"schema-validated scores" premise therefore does not hold for precisely the values that break ordering.
**Evidence:** `test_e1_nan_scores_accepted_rerank_and_audit`, `test_e2_infinite_scores_accepted_and_rank_dominance`
(both PASS at `8f788c5` — they pin the accept-as-success behavior). Live run: `round(nan, 4) == nan`; sorted
output carries the nan magnitude to the top.
**Severity:** HIGH (fallback contract bypass + audit integrity + rank poisoning).
**Resolution (additive):** set `Field(allow_inf_nan=False)` on `RerankScores.scores`. Non-finite input then fails
`model_validate`, lands on validation retry → `validation_exhausted` → the deterministic lexical fallback, no
audit. This CHANGES observable semantics for non-finite scores (from "rerank" to "fallback") — flag as a
compliance note to contract B (the intent of "schema-validated scores; never raises" is satisfied, not violated).

### FB-M2.2-2 — HIGH — Rerank tie-break drops `tier_order`; a raw trace outranks a verified memory at equal score
**Location:** `src/jarvis/kernel/memory_retrieval.py:177-180`:
`sorted(zip(candidates, scores), key=lambda pair: (-round(float(pair[1]), 4), pair[0].event_id))`.
**Failure mode:** the ratified total order is `(-score, tier_order, event_id)` with `tier_order` memory<trace —
the FB-1 discriminator this package exists to deliver. The lexical core applies it (`:254`), but the model
rerank sort key uses **only** `(rounded_score, event_id)`. When a model returns equal scores for a verified
memory and a raw trace, the pair is ordered by event_id — a trace whose id sorts earlier is returned ABOVE the
verified memory. Even a rerank that returns score-preserving output silently inverts verification priority.
**Evidence:** `test_b2_rerank_equal_scores_drop_tier_order_trace_wins` (PASS at `8f788c5`): `[tier for hit] ==
["trace", "memory"]` with equal model scores. 
**Severity:** HIGH (contract-order violation on the seam; FB-1 discriminator inverted).
**Resolution (additive):** extend the rerank sort key to `(-round(score,4), TIER_ORDER[candidate.tier],
candidate.event_id)` — aligns the seam with the contract's own stated order. No other caller-visible change.

### FB-M2.2-3 — MEDIUM — The audit write drifts the NAT-03 digest; contract D's "digest inputs unchanged" is false
**Location:** `src/jarvis/kernel/memory_retrieval.py:260-274` (audit `log.append`); digest fields at
`memory_index.py:38-42` and `memory_projection.py:56-60`.
**Failure mode:** the audit event is appended to the **same** `memory` stream/`EventLog` the folds are read
from. `MemoryIndex.digest()` and `MemoryProjection.digest()` hash `last_seq, event_count, streams, …`, so every
genuine reranked retrieve bumps `last_seq`/`event_count`/`streams["memory"]` and the tract digest DRIFTS — and
drifts again on every later rerank on the same log. Contract D states the audit "does not enter MemoryIndex
folds … digest inputs unchanged": fold predicates are unchanged (probe F4 — that half holds), but the digest
input claim does not.
**Evidence:** `test_f5_audit_changes_index_digest_metadata` (PASS at `8f788c5`): `d0 != d1 != d2` across two
reranked calls; `event_count` 4→6; `streams["memory"]` 4→6.
**Severity:** MEDIUM (recovery/compare consumers using MemoryIndex.digest() get a moving target; repeated
reranks each re-dirty the digest).
**Resolution (additive, needs creator ruling):** (a) record `memory.retrieve.reranked` on a separate
management stream (e.g. `"memory.audit"`) so `streams["memory"]` and the projected digest stop moving — this
changes contract D payload stream only, flagged; or (b) accept and amend contract D wording ("digest inputs
unchanged" → fold inputs unchanged) with creator sign-off; or (c) exclude `last_seq/event_count/streams` from
the M2.2 digest (NOT additive — violates M2.1). Recommend (a) or (b); do not touch digest hashing.

### FB-M2.2-4 — MEDIUM — The default facade path runs the model but silently drops the audit event
**Location:** `src/jarvis/kernel/memory_api.py:75-102` — `Memory.retrieve(..., log: EventLog | None = None)`.
**Failure mode:** contract D: "When a model rerank actually RUNS … append ONE audit event." The natural usage
`Memory(log=log).retrieve(query, ranker=ranker)` runs the real model rerank (`last_result.reranked=True,
adapter called`) but writes **no** audit event because `log` defaults to `None` on the facade and the facade
never forwards its own underlying log. The default path inverts the dependency: audit (the M2.9 ledger
evidence) is silently skipped exactly where it is most likely to be missed.
**Evidence:** `test_f1_default_facade_path_runs_model_but_drops_audit` (PASS at `8f788c5`): `fake.calls == 1`,
`reranked is True`, `log.replay()` contains no `memory.retrieve.reranked`.
**Severity:** MEDIUM (audit evidence silently conditional on caller remembering an extra kwarg).
**Resolution (additive):** when the facade was constructed with a log (or index), default `log=` to that log,
or accept an explicit `audit=True/None` tri-state and log the omission. Minor contract-D clarification: audit
still only when a model ran.

### FB-M2.2-5 — MEDIUM — A duplicate event_id across both fold dicts serves a trace as a "verified" memory
**Location:** `src/jarvis/kernel/memory_retrieval.py:204-216` (`_tier_for` answers from `memories` membership
only) combined with `:237` `combined = {**memories, **traces}` (trace wins the content merge).
**Failure mode:** `retrieve(memories=, traces=)` is a public kernel API. If the same event_id is present in
both maps, the TRACE payload wins the merge (content is raw-trace content) yet `_tier_for` returns
`("memory", True)` — a raw trace served as a gate-passed, committed, verified memory. Not reachable through a
real append-only log (verified live: `EventLog.append` enforces `event_id TEXT UNIQUE`, so a real replay can
never produce both folds under one id), but reachable by any future consumer that builds fold maps directly
(M2.3 consolidation reads this seam).
**Evidence:** `test_c1_dual_fold_id_trace_content_labeled_verified_memory` (PASS at `8f788c5`): hit content is
the trace's, `tier=="memory"`, `verified is True`.
**Severity:** MEDIUM (verification-label spoof on a caller-input surface; latent for M2.3).
**Resolution (additive):** cross-fold guard in the candidate funnel — a key present in both maps is a fold
integrity error (typed failure) or explicitly de-duplicated with memories winning BOTH content and tier.
Flag as contract note (the union merge rule for overlapping ids is currently under-specified).

### FB-M2.2-6 — LOW — Lax coercions: bool→float and numeric-string→float scores, int/str→bool `verified`
**Location:** `memory_retrieval.py:118` (`scores: list[float]`, lax), `:71` (`verified: bool`, lax).
**Failure mode:** `[True, False]` → `[1.0, 0.0]`, `["0.9", "0.1"]` → `[0.9, 0.1]`, `verified=1` → `True`,
`verified="false"` → `False` (all verified live). The "schema-validated" boundary accepts type-smuggled input
rather than rejecting it, so the validation-fallback path (FB-M2.2-1's buddy) is narrower than the docs imply.
**Evidence:** `test_e8_bool_scores_coerce_to_float`, `test_e9_numeric_string_scores_coerce_to_float`,
`test_c3_verified_bool_lax_coercion` (PASS at `8f788c5`).
**Severity:** LOW.
**Resolution (additive):** strict sub-schemas on the model-facing contract only
(`Annotated[float, Field(allow_inf_nan=False)]`, strict acceptance of bool/str is a tightening that changes
non-finite/type-smuggled handling → flag with FB-M2.2-1).

### FB-M2.2-7 — LOW — Rerank audit is hard-stamped with the creator principal
**Location:** `memory_retrieval.py:265` (`principal_id=CREATOR_PRINCIPAL_ID`).
**Failure mode:** every `memory.retrieve.reranked` event is authored as `creator` regardless of the actual
calling principal. A future agent-triggered rerank leaves false creator-authored provenance on the audit
trail (provenance discipline matches M2.1's trace-writer which DOES accept a principal).
**Evidence:** `test_f6_audit_stamped_creator_principal` (PASS at `8f788c5`).
**Severity:** LOW.
**Resolution (additive):** accept the caller's principal id on `retrieve()`/`Memory.retrieve` and stamp it.

### FB-M2.2-8 — LOW — Malformed fold payload raises a raw pydantic exception on a public seam
**Location:** `memory_retrieval.py:196-201` (`_UnionView` shim) — `retrieve()` with a non-dict payload value
raises `ValidationError` instead of a typed failure.
**Failure mode:** `retrieve({"A": "not-a-dict"}, {}, "anything")` → `pydantic.ValidationError`. Unreachable via
the append-only log (writers store typed events), but the public `retrieve(memories=, traces=)` API accepts
caller maps and re-exposes the raw exception, which is inconsistent with the kernel's typed-failure
discipline elsewhere.
**Evidence:** `test_h2_malformed_non_dict_fold_payload_raises_untyped` (PASS at `8f788c5`).
**Severity:** LOW.
**Resolution (additive):** wrap fold-map validation in a typed `RerankFoldError`/`ValueError` path.

### FB-M2.2-9 — INFO — Unicode-only content is invisible to the lexical funnel (module-11 parity preserved)
**Location:** `memory_query.py:38-40` (`_WORD = re.compile(r"[a-z0-9]+")`, frozen).
**Failure mode:** CJK-only memory/query → score 0 → never retrieved. Mirrors M2.1 `recall` byte-for-byte, so the
parity promise holds; it is a frozen module-11 limitation the rerank seam cannot fix (the model never sees those
candidates).
**Evidence:** `test_h3_unicode_only_content_never_retrieved` (PASS at `8f788c5`).
**Severity:** INFO (documented limitation; no action in M2.2).

### FB-M2.2-10 — INFO — `role_contracts` merge can shadow `SCHEMA_CONSTRAINED`; M1 default is preserved
**Location:** `model_gateway.py:212-228` (`route_table = {**M1_ROLE_CONTRACTS, **role_contracts}`).
**Failure mode / evidence:** with `None` the M1 route resolves exactly (`test_d1`, PASS); a caller-supplied
override CAN re-point the frozen `SCHEMA_CONSTRAINED` role at another contract for one call (`test_d2`, PASS —
route consult-then-replace is proven because the overwritten route (`fs.write`) yields `adapter_error`, not a
`no_provider` on `schema_constrained`). This is the RATIFIED merge order (contract A) and is additive-only, but
it is the single seam where a shared/buggy `role_contracts` dict built over `M2_ROLE_CONTRACTS` could one day
move module-6's role off `model.generate_structured`. Partial overrides lacking `RERANK` fall back safely
(`test_d3`, PASS — no dial, no audit, deterministic lexical output).
**Severity:** INFO (compliant today; guard: never persist a merged role table as module state, keep the merge
per-call as implemented).

---

## 3. Attack-surface sweep — what held (adversarial PASS pins)

These are kept as regression pins in `tests/review/test_freebuff_redteam_m2_2.py`:

| Surface probed | Probe(s) | Outcome at `8f788c5` |
| :--- | :--- | :--- |
| Hermeticity: no log mutation / no ULID / no clock on NoOp path | A1 | PASS (replay byte-identical) |
| Determinism: twice + across fresh rebuild of same db | A2 | PASS |
| Module-11 byte parity on trace-free log | A3 | PASS |
| Offline: bogus backend never dialled, no audit | A4, E7 | PASS |
| Caller fold dicts never mutated (incl. model + audit path) | A5 | PASS |
| Offline total order `(-score, tier, event_id)` | B1 | PASS |
| Deterministic reorder on distinct model scores | B3 | PASS |
| `RankedMemory` Literal tier + `extra="forbid"` | C2 | PASS |
| Lens/string-coercion pins (E8/E9/C3) | E8/E9/C3 | PASS |
| Score-count mismatch → lexical fallback, no audit | E3 | PASS |
| `validation_exhausted` after 3 garbage attempts | E4 | PASS |
| `transport_error` / `adapter_error` → fallback, no raise | E5/E6 | PASS |
| Empty candidates / huge limit / negative scores | E11/E12/E10 | PASS |
| Custom ranker raising propagates (only `ModelRetrievalRanker` is never-raise) | E13 | PASS |
| Offline never audits; audit payload field sanity (pre-rerank id list, provider/contract/version/limit) | F2/F3 | PASS |
| Audit stays out of the memory/trace folds | F4 | PASS |
| RankedHit fields == `memory.get()` payload shape | H1 | PASS |

## 4. Evidence retained

- `tests/review/test_freebuff_redteam_m2_2.py` — 36 behavioral probes. Assertions on current behavior that a
  corrective fix is expected to flip carry `# FLIPS ON FIX` (FB-M2.2-1 `E1/E2`, FB-M2.2-2 `B2`, FB-M2.2-3
  `F5`, FB-M2.2-4 `F1`, FB-M2.2-5 `C1`, FB-M2.2-6 `E8/E9/C3`, FB-M2.2-8 `H2`); the rest are regression pins for
  behavior judged contract-compliant.

## 5. Verdict

**M2_2_RECONCILIATION_REQUIRED.** The deterministic core, hermiticity, fallback discipline, and additive seam
discipline held under attack. But M2.2 fails on its own two promises under adversarial input: the rerank seam
can invert the FB-1 verified-over-trace discriminator (FB-M2.2-2, HIGH) and treats NaN/±inf scores as a
successful, audit-worthy model rerank (FB-M2.2-1, HIGH). The audit trail both skips by default (FB-M2.2-4) and
dirtied the digest it was promised not to touch (FB-M2.2-3).

**Most dangerous attack (if any single one):** **FB-M2.2-1 + FB-M2.2-2 combined** — a hostile or defective
rerank provider returns NaN (or equal) scores: the deterministic lexical fallback is bypassed, ordering can be
driven arbitrarily (task-relevant raw traces pushed above verified memories via crafted/equal scores), NaN is
spliced into consumed memory state, and the audit trail records the garbage as a genuine rerank. That is the
package's evidence and ranking integrity surface being spoofable by the seam it exists to abstract.