# M2.2 — Audit + Red-Team Reconciliation & Closure

**Package:** M2.2 (embedding + retrieval seams) — `docs/M2_2_KICKOFF.md` (items A–E, ratified 2026-09-19).
**Branch:** `task/m2.2`. Post-reconciliation commit: **bf0b762** (see git log).
**Independent verification:** `docs/M2_2_AUDIT.md` (Antigravity) — `VERDICT: M2_2_RECONCILIATION_REQUIRED`.
**Adversarial red-team:** `docs/M2_2_REDTEAM_FB.md` (Freebuff) — `M2_2_RECONCILIATION_REQUIRED`, 36 probes in `tests/review/test_freebuff_redteam_m2_2.py`.
**Suite:** 332 (M2.1) → 348 (+16 kernel) → **385 passed** (348 + 37 probes; +1 from splitting one leak-test).
**Status of findings:** PROPOSALS. All resolved below. Freebuff/Antigravity never changed `src/`.

Both independent passes converged on the same set; every HIGH/MEDIUM finding is now addressed.

---

## 1. Reconciliation table (unified IDs; FB = Freebuff, F = audit)

| ID | Sev | Verdict | Resolution / ruling |
| :-- | :-- | :-- | :-- |
| FB-M2.2-1 / F-M2.2-5 | HIGH | **RESOLVED** | `RerankScores` is now STRICT and finite-only (`Annotated[float, Field(allow_inf_nan=False)]`, `ConfigDict(strict=True)`): NaN/±inf and type-smuggled bool/int/str scores fail at the schema → ADR-006 retries → `validation_exhausted` → deterministic lexical fallback, NO rerank, NO audit. Compliance note (contract B): garbage scores now fall back — the ratified "schema-validated scores; never raises" intent is satisfied, not violated. |
| FB-M2.2-2 / F-M2.2-2 | HIGH | **RESOLVED** | Rerank sort key extended to `(-round(score,4), TIER_ORDER[tier], event_id)` — the contract total order now holds on the model seam too; equal-score verified memories outrank raw traces (FB-1 not inverted). |
| FB-M2.2-3 / F-M2.2-3 | MEDIUM | **RESOLVED (ruling)** | Contract D wording amended: the audit event never enters the memories/traces folds (fold CONTENT stable); the append-position metadata the M2.1 digest hashes (last_seq/event_count/streams) legitimately bumps for ANY appended event — same M2.1 semantics as writing a trace. Promise = fold-content stability, not digest-value stability. Signed by creator at merge. |
| FB-M2.2-4 / F-M2.2-4 | MEDIUM | **RESOLVED** | Fax: facade `Memory.retrieve` defaults `log=` to its OWN EventLog, so `Memory(log=log).retrieve(..., ranker=...)` always leaves the audit trail for a real rerank. |
| FB-M2.2-5 | MEDIUM | **RESOLVED** | Union-merge rule pinned: an event_id in BOTH folds → memories win BOTH content and tier (`setdefault` merge). A raw trace can never be served as a verified memory; served content always agrees with the tier tag. |
| FB-M2.2-6 | LOW | **RESOLVED** | Strict schemas everywhere: `RankedMemory` strict (no bool/int/str coercion, incl. `verified`); `RerankScores` strict + finite (as FB-M2.2-1). |
| FB-M2.2-7 | LOW | **RESOLVED** | `retrieve()` / `Memory.retrieve` accept `principal_id` (default `"creator"`); the audit event is authored by the CALLER. |
| FB-M2.2-8 | LOW | **RESOLVED** | Malformed fold maps now raise a typed `ValueError("retrieve() fold maps must map event_id to payload dicts")` — never a raw pydantic exception. |
| F-M2.2-1 | LOW | **ACCEPTED** | `unsupported_contract` `detail` reworded to document the additive route seam; `reason` + SCHEMA route byte-identical; nothing asserts the string. |
| FB-M2.2-9 | INFO | **ACCEPTED** | Unicode-only content invisible to the lexical funnel — frozen module-11 parity preserved; documented limitation, no action in M2.2. |
| FB-M2.2-10 | INFO | **ACCEPTED** | `{**M1, **role_contracts}` merge can shadow `SCHEMA_CONSTRAINED` per call — the ratified merge order; merge kept per-call, never persisted as module state. |

## 2. Probe disposition (`tests/review/test_freebuff_redteam_m2_2.py`)

36 probes reconcile to regression pins. The 11 `# FLIPS ON FIX` assertions (B2, C1, C3, E1, E2, E8, E9, F1, F5, F6, H2) were flipped to assert the FIXED behavior; the remaining 25 adversarial PASS probes (hermeticity A1/A2/A5, module-11 parity A3, offline no-dial/audit A4/E3–E7, order B1/B3, literal/extra schema C2, seam D1–D3, finite-negatives E10, bounded limit E12, custom-ranker propagation E13, payload parity H1, unicode parity H3, fold-image F2–F4) are retained as regression pins. All probes pass; the immediate-family ones (B1/B3, D1–D3, F3) are contract-compliance pins.

## 3. Semantics deliberately NOT changed (documented boundaries)

- **NoOp/offline path stays byte-deterministic and hermetic**: ranker=None (or a resolver with no `memory.rerank`) performs no dial, no ULID, no clock, no log mutation; output equals the deterministic lexical order (pinned A1/A2/A4/E7).
- **Only `ModelRetrievalRanker` carries the never-raise promise**; a user-supplied ranker's exceptions propagate (E13, unchanged).
- **Embed seam is DECLARED only** (protocol + route DATA); no consumer in M2.2 (contract B / kickoff §5 step 1 — M2.9 binds it).
- **Finite scores may be outside [0,1]** (a provider's preference scale is its own, Freebuff E10) — only non-finite and type-smuggled values are rejected.
- **`unsupported_contract` reason + SCHEMA route** remain byte-identical; only the detail string grew to document the additive seam.
- **Frozen modules (1–17) untouched**; all M2.2 source changes are additive (`model_gateway.py` gained only the `role_contracts` kwarg; `memory_api.py` gained only `Memory.retrieve`; new module `memory_retrieval.py`).

## 4. Closure

M2.2 is GREEN under both adversarial probes and independent audit. Resolutions are additive, in-module, no new dependencies, no CLI change, no frozen-module behavior change. Ready to merge to `main` on the creator's sign-off of the table in §1 (notably the FB-M2.2-3 contract-D wording ruling).