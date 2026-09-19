# M2.2 Audit — Independent Verification (Antigravity)

**Target:** `task/m2.2` @ `8f788c5` (unmerged; additive to main @ `838d182`).
**Contract:** `docs/M2_2_KICKOFF.md` items A–E (ratified) + `docs/M2_KICKOFF.md`.
**Verifier:** Antigravity (independent; no src/test modified; only this report written).
**Date:** 2026-09-19
**Also on record:** `docs/M2_2_REDTEAM_FB.md` (Freebuff, adversarial — corroborates the blocking items; probes in
the untracked `tests/review/test_freebuff_redteam_m2_2.py`).

## Method

- Re-derived the contract from `docs/M2_2_KICKOFF.md` items A–E and `docs/M2_KICKOFF.md`; all claims checked
  against code at commit `8f788c5`, never against commit-message text.
- Diff audited: `git diff 838d182 8f788c5` — exactly 5 files touched
  (`model_gateway.py`, `memory_api.py`, `memory_retrieval.py` [new],
  `tests/kernel/test_memory_retrieval.py` [new, 16 tests], `docs/M2_2_KICKOFF.md`). No `pyproject.toml` diff
  (no new deps), no `cli.py`/`memory_query.py`/`memory_trace.py`/`memory_index.py`/`event_log.py`/
  `done_gate.py`/`intent.py` change.
- Full + focused suites run independently; blocking claims re-verified first-hand (live repro below).

## Verification-environment note (important)

- Committed M2.2 suite = **348 tests** (332 M2.1 baseline + 16 new). Observed **348 passed**, repeatable.
- An **UNTRACKED, actively-edited** `tests/review/test_freebuff_redteam_m2_2.py` (Freebuff probes; mtime moved
  09:08→09:11 during this review; not in `8f788c5`) is collected via `testpaths=["tests"]`. Transient failures
  appeared while Freebuff was editing it; once settled, the worktree is stable at **384 collected / 384 passed**
  (332 + 16 + 36 probes) across nine consecutive full runs; probes alone pass 36/36 ×5. No `pytest-randomly`,
  no `addopts`, so ordering is pytest's default stable file-name order.
- `docs/M2_2_REDTEAM_FB.md` also appeared (untracked) during review; its probe-pinned behaviors confirm the
  findings below.

## Item verification (contract A–E)

### A. `role_contracts` additive kwarg — PASS
`model_gateway.py:208` adds `role_contracts: dict[RoleContract, tuple[str,str]] | None = None`. Default path
(`model_gateway.py:212-217`) uses `M1_ROLE_CONTRACTS` itself → identical route and downstream flow on the
SCHEMA_CONSTRAINED route. `M1_ROLE_CONTRACTS` unchanged (`model_gateway.py:105-107`). Route DATA lives in
`memory_retrieval.py:54-58` (`M2_ROLE_CONTRACTS`, `{**M1, **{RERANK, EMBED}}`), never hardcoded in module 6.
Only delta is an `unsupported_contract` `detail` reword (`:222-225`); `reason` unchanged; nothing asserts it.

### B. `retrieve()` deterministic core — PASS for core; FAIL for the model seam (blocking)
- Core: total order `(-score, tier_order, event_id)` at `memory_retrieval.py:254`, `TIER_ORDER` memory=0
  trace=1 (`:48`). No clock/RNG/ULID/network (imports audited); deterministic across rebuild
  (`test_retrieve_deterministic_across_rebuild`). Limit validation matches the M2.1 C4 rule
  (`:234-235` == `memory_api.py:71-72`). Lexical funnel reuses module-11 recall over the same union
  (`:238-240`); no-trace parity pinned (`test_retrieve_matches_module11_lexical_when_no_traces`). Tier/verified
  provenance correct over real logs: `MemoryIndex` folds only `memory.write.committed`/`memory.trace.recorded`
  (`memory_index.py:58-61`); traces never verified.
- Model seam FAILS the same order on equal scores: sort key is `(-round(score,4), event_id)`
  (`memory_retrieval.py:179`) — `tier_order` is dropped, so a raw trace with an earlier event_id outranks a
  verified memory. **Reproduced live**: same two hits → core key yields `['memory','trace']`; rerank key yields
  `['trace','memory']`. This inverts the FB-1 discriminator M2.2 exists to deliver, deterministically, even for
  a score-preserving/equal-score model rerank. (Freebuff probe `test_b2`, same result.) Blocking, see FB-1.

### C. Facade additive; `recall()` untouched — PASS
`Memory.retrieve` (`memory_api.py:75-102`) is new; `recall()` (`:70-73`) byte-identical to M2.1
(verified vs `git show 838d182`). Same combined view; projection fallback mirrors `_combined()`.

### D. Rerank audit — partial FAIL (blocking + contract-wording conflict)
- Payload correct when it fires: `provider_id`/`contract_id`/`contract_version` (ACTIVE provider, F3/F14,
  `model_gateway.py:349-357`)/`candidate_event_ids`/`limit` (`memory_retrieval.py:266-272`); stream
  `memory`, once per real rerank; pinned by `test_model_rerank_reorders_and_audits`.
- **Audit is silently skipped on the natural facade usage** `Memory(log=log).retrieve(query, ranker=ranker)`:
  facade `log=` defaults to `None` and is never defaulted to the facade's own log, so a real model rerank runs
  (`reranked=True`) with NO audit event. Contract D ("When a model rerank actually RUNS … append ONE audit
  event") is unmet on the default path. Freebuff probe `test_f1` pin. Blocking, see FB-4.
- **Audit events never enter the memories/traces folds**: fold predicates unchanged (`memory_index.py:58-61`).
  But appending to the same `memory` stream bumps `last_seq`/`event_count`/`streams["memory"]`, which ARE
  `MemoryIndex.digest()` inputs → the NAT-03 memory-tract digest drifts on each real rerank, contradicting
  contract D's "digest inputs unchanged". "Append on stream memory" + "digest unchanged" are mutually
  incompatible as ratified; needs creator ruling (separate audit stream, or wording amendment). Freebuff probe
  `test_f5` pin. Blocking until ruled, see FB-3.

### E. No new CLI / deps — PASS
`pyproject.toml` diff empty; `cli.py` untouched; no new entry points.

## Hermeticity & fallback code paths (read + tested)

- Offline (`ranker=None` or no provider): `ModelRetrievalRanker.rerank` → `generate_structured` returns
  `TypedFailure("no_provider")` before any `adapter.invoke` (`model_gateway.py:234-240`); bomb never dialled,
  no audit, no mutation (`bomb.calls == 0`; Freebuff A1 confirms replay byte-identical).
- Fallback on `TypedFailure` (`:166-169`) and len-mismatch (`:172-175`) returns unchanged lexical
  `candidates[:limit]`, `reranked=False`, never raises, no partial reorder. `transport_error`/`adapter_error`/
  `validation_exhausted` all land lexical (Freebuff E3–E6).

## Live reproductions (this review)

```
nan accepted: [nan, 0.5]            # RerankScores.model_validate
bool coerced: [1.0, 0.0]            # [True, False] -> floats
str coerced:  [0.9, 0.1]            # ["0.9","0.1"] -> floats
core sort (-score, tier_order, event_id) -> ['memory','trace']   # contract order
rerank sort (-score, event_id)         -> ['trace','memory']     # FB-1 inverted
```

## Test results observed (independent runs)

- Committed M2.2 suite: **348 passed**. M2.2 file alone: **16 passed** twice.
- Focused frozen regression set (module 6 + memory_api/index/projection/query/trace/write + model_answer):
  **86 passed** = 16 new + **70 pre-existing, zero regressions** (pre-existing files byte-identical to M2.1).
- Current worktree incl. untracked Freebuff probes: **384 collected / 384 passed**, stable ×9; probes alone 36/36 ×5.

## Findings

| ID | Sev | Item / invariant | Evidence | Note |
| :-- | :-- | :-- | :-- | :-- |
| FB-M2.2-1 (F-M2.2-5) | **HIGH** | B — "schema-validated scores"; D — audit only on real rerank | `memory_retrieval.py:113-118` | `RerankScores.scores: list[float]` accepts NaN/±inf (and bool/numeric-string coercions). A model emitting NaN is treated as a SUCCESS: no lexical fallback, NaN spliced into returned `RankedMemory.score`, and `memory.retrieve.reranked` fires attesting a genuine rerank on garbage. Additive fix: `Field(allow_inf_nan=False)` + strict float on the model-facing schema. |
| FB-M2.2-2 (F-M2.2-2) | **HIGH** | B — total order `(-score, tier_order, event_id)` | `memory_retrieval.py:179`; repro above | Rerank tie-break drops `tier_order` → equal-score raw trace outranks verified memory (FB-1 inverted on the seat of the package). Live repro: core `['memory','trace']`, rerank `['trace','memory']`. Additive fix: extend sort key to `(-round(score,4), TIER_ORDER[tier], event_id)`. |
| FB-M2.2-3 (F-M2.2-3) | MEDIUM | D — "digest inputs unchanged" | `memory_index.py:38-42,57-61`; `memory_retrieval.py:260-274` | Audit append drifts `MemoryIndex.digest()` (`last_seq`/`event_count`/`streams["memory"]`) on every real rerank; fold CONTENT unchanged. Contract clauses "append on stream memory" + "digest unchanged" are incompatible as ratified. Needs creator ruling: separate `memory.audit` stream or wording amendment → fold inputs unchanged. |
| FB-M2.2-4 (F-M2.2-4) | MEDIUM | D — "when a model rerank actually RUNS … append ONE audit event" | `memory_api.py:75-102` | Default facade usage `Memory(log=log).retrieve(query, ranker=ranker)` runs the model but writes no audit (`log=` defaults None, never forwards the facade's log). Additive fix: default `log=` to the facade's own log (or explicit audit tri-state). Freebuff probe `test_f1`. |
| FB-M2.2-5 | LOW | B — fold-membership tier rule (latent) | `memory_retrieval.py:204-216,237` | If a caller supplies an event_id in BOTH fold maps, content comes from the trace (`{**memories, **traces}`) yet tier/verified = memory/True — trace served as verified memory. Unreachable via the append-only log (event_id UNIQUE); latent for M2.3 direct fold building. Additive guard/typed-failure advised; flag union-merge rule as under-specified. |
| FB-M2.2-6 | LOW | B — schema strictness | live repro | bool→float, `"0.9"`→float lax coercions at the rerank schema and `verified: bool`. Tighten with the FB-M2.2-1 schema fix. |
| FB-M2.2-7 | LOW | D — provenance | `memory_retrieval.py:265` | Audit stamped `CREATOR_PRINCIPAL_ID` unconditionally. Matches the M2.1 writer pattern (caller-principal param exists there); future agent-triggered reranks need a caller principal. |
| FB-M2.2-8 | LOW | kernel typed-failure discipline | `memory_retrieval.py:196-201` | `retrieve(memories=, traces=)` with a non-dict payload raises raw `pydantic.ValidationError` (`_UnionView`). Untyped surface; wrap in a typed failure. |
| F-M2.2-1 | LOW | A — additive byte-identical | `model_gateway.py:222-225` | `unsupported_contract` detail reworded; reason + SCHEMA route byte-identical; nothing asserts it. Cosmetic. |
| FB-M2.2-9 | INFO | parity | `memory_query.py:38-40` | Unicode-only content never retrieved — mirrors frozen module-11 exactly; documented limitation, no action. |
| FB-M2.2-10 | INFO | A — merge order | `model_gateway.py:212-228` | Caller `role_contracts` can shadow `SCHEMA_CONSTRAINED` per call — the ratified merge order; additive-only. Guard: keep merge per-call, never persist as module state. |

## Verdict

Blocking discrepancies confirmed against the ratified contract on the package's own reason-for-being:
- Contract B: the model-seam rerank produces an order violating `(-score, tier_order, event_id)` and inverts the
  FB-1 verified-over-trace discriminator (FB-M2.2-2, HIGH; live reproduction).
- Contract B+D: NaN/±inf (and type-coerced) scores pass "schema-validated", bypass the promised lexical
  fallback, and fire a success audit on garbage (FB-M2.2-1, HIGH; live reproduction).
- Contract D: the default facade path runs a real rerank with no audit event (FB-M2.2-4), and the audit write
  drifts the NAT-03 digest the contract said unchanged — a contract-wording conflict needing a creator ruling
  (FB-M2.2-3).

The deterministic core, hermeticity, fallback-on-typed-failure discipline, additive seams, scope discipline,
and zero frozen-module regressions all held (348 committed / 384 worktree green; 70 pre-existing module-6/
memory/module-11 tests unchanged).

`VERDICT: M2_2_RECONCILIATION_REQUIRED`

Exact reconciliation needed (all additive; no frozen module touched, no new deps):
1. **FB-M2.2-2**: extend the rerank sort key in `ModelRetrievalRanker.rerank` to
   `(-round(score,4), TIER_ORDER[candidate.tier], candidate.event_id)` — aligns the seam with contract B's own
   total order; flip red-team probe `test_b2` to assert `["memory","trace"]`.
2. **FB-M2.2-1/6**: tighten the model-facing rerank schema to reject non-finite and non-plausible types
   (`Field(allow_inf_nan=False)`, strict float) so garbage lands on `validation_exhausted` → lexical fallback,
   no audit; flip probes `test_e1/test_e2/test_e8/test_e9`. Add a compliance note that non-finite scores now
   fall back (contract B intent satisfied, not violated).
3. **FB-M2.2-4**: default the facade's `log=` to the facade's own log (or an explicit audit tri-state) so the
   natural usage `Memory(log=log).retrieve(...)` audits a real rerank; flip probe `test_f1`.
4. **FB-M2.2-3 (creator ruling)**: either route `memory.retrieve.reranked` to a separate `memory.audit` stream
   so `streams["memory"]`/the memory-tract digest stop moving, or amend contract D wording ("digest inputs
   unchanged" → "fold inputs and retrieval content unchanged") and record the ruling; flip probe `test_f5`
   per ruling.
5. Optional non-blocking: typed fold-error for malformed payloads, caller-principal audit stamping, cross-fold
   id guard for M2.3, `unsupported_contract` detail stability.