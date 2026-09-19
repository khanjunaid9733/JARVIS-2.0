# M2.3 — Consolidation Pipeline — Reconciliation Record

**Status:** reconciliation landed on `task/m2.3` (uncommitted follow-up to
`c78f406`); creator ratification of the amendment record (`M2_3_KICKOFF.md` §7
items 1–9) plus merge to `main` pending.
**Inputs:** Freebuff red-team `docs/M2_3_REDTEAM_FB.md` (FB-M2.3-1..11,
**M2_3_RECONCILIATION_REQUIRED** — 0 CRITICAL, 0 HIGH, 7 MEDIUM, 2 LOW, 2 INFO)
and Antigravity audit `docs/M2_3_AUDIT.md` (F-M2.3-1..11, **M2_3_RECONCILIATION_REQUIRED**
— 7 MEDIUM, 3 LOW, 1 INFO). Both ran read-only against branch `task/m2.3` @ `c78f406`.
**Verdicts concurred on every substantive finding** (FB-M2.3-* pairs with F-M2.3-* below).

The two reports are evidence, not law: each finding is a PROPOSAL with a resolution.
This record is the assistant's response under each: **LANDED** (implemented in-module),
**DATA** (recast as a policy datum rather than a hardcoded branch), **DOC** (contract
wording amended, no code change), or **ACCEPT** (documented, no action).

---

## 1. Decisions

| Finding | Severity | Ruling | Resolution (landed on `task/m2.3`) |
| :--- | :--- | :--- | :--- |
| FB-M2.3-1 · F-M2.3-2 | MEDIUM | **LANDED** | **One consolidation, one principal.** The effective principal is resolved once at construction (`principal_id or policy.principal_id`) and stamps the promotion chain AND the `memory.consolidate.*` audit events. Probes E1/E2 flipped: `audit_principals == {"drone"}`, `audit[0].principal_id == "drone"`. |
| FB-M2.3-2 · F-M2.3-1 | MEDIUM | **LANDED** | **`any_key_same_source` restored.** `ContradictionRule.gate` now accepts all three ratified values; the evaluation branch keys on source-equality (any key once the source matches). Probe B1 flipped. |
| FB-M2.3-3 · F-M2.3-5 | MEDIUM | **LANDED** | **Success bookkeeping from committed provenance.** The already-superseded set is seeded from each committed memory's own `provenance.superseded` (the authoritative record) and the reconciling pass also seeds the run-internal set from the same field — the audit event is optional, provenance is not. `audit=False` can no longer split-brain and `provenance.superseded` is bounded. Probe A2 flipped. |
| FB-M2.3-4 · F-M2.3-6 | MEDIUM | **DATA (creator ratifies in amendment item 4)** | **Consolidation-products excluded from same-key supersession by default.** A product is any memory whose provenance carries `evidence_ids`. `supersede_refine_gap: float \| None` (new policy field, default `None`) is the data switch: products are superseded ONLY when a confidence gain ≥ gap is declared — a stable fact is promoted once and refined only on a policy-declared gain, never churned. Probe A3 flipped. |
| FB-M2.3-5 · F-M2.3-3 | MEDIUM | **LANDED** | **Sticky rejection marker.** A failed promotion appends a `memory.consolidate.rejected` diagnostic event ONCE carrying the candidate's evidence ids; the consume scan honors marker evidence_ids, so re-running an unchanged log appends zero events even when the pre-check gate and the writer gate disagree (idempotency no longer conditional on gate coincidence). Probe A4 flipped. |
| FB-M2.3-6 · F-M2.3-7 | MEDIUM | **DOC (FB-M2.2-3 ruling re-applied)** | **Contract rewording, not index code.** Item E.4/C now promise fold-INPUT/fold-CONTENT stability: the audit events never enter the `memories`/`traces` folds (R2 held throughout), while `event_count`/`streams`/`digest()` legitimately move with any appended event — the M2.1 contract, unchanged. No flip: probe D1 stays a PASS pin (fold stable, digest deterministic, metadata moves). |
| FB-M2.3-7 · F-M2.3-8 | LOW | **LANDED** | **Three strictly distinct normalize modes.** `exact` = strip only (whitespace AND case preserved), `lower` = strip + casefold (whitespace preserved), `fold` = strip + whitespace-collapse + casefold. Probe B2 flipped. |
| FB-M2.3-8 · F-M2.3-4 | MEDIUM | **LANDED** | **Provenance-guard against shape abuse.** Reference extraction is shape-typed: a bare string is ONE reference (never scanned char-by-char), a list/tuple keeps only string refs, any other shape yields no refs — it can never raise on the public seam and can never silently re-promote a referenced trace. Probes C1/C2 flipped. |
| FB-M2.3-9 · F-M2.3-9 | LOW | **LANDED (opt-in datum; creator ratifies in amendment item 9)** | **`promote.order: log \| confidence_desc`.** Log order (prior behavior, now the disclosed default) or a policy-declared priority for cap allocation. Probe A5 unchanged (boundary pin + documented default). |
| FB-M2.3-10 · F-M2.3-10a | INFO | **ACCEPT (documented)** | The promoted memory's raw content is the cluster's last trace in log order (`members[-1]`), verbatim, per-log deterministic and internally consistent. Kept (no creator preference to pick a different datum); probe E3 stays. |
| FB-M2.3-11 · F-M2.3-10b | INFO | **ACCEPT (already gone)** | The rewrite performs a SINGLE `log.replay()` pass (the `MemoryIndex.rebuild` call was dropped); the double full-log replay cost no longer exists on this branch. |
| F-M2.3-11 | LOW | **ACCEPT (process)** | The adversarial worktree landed untracked mid-audit; the committed-target count (399) was and remains reproducible. Reconciliation re-freezes at the reconciliation commit; the merge gate re-verifies at `main` before state update. |

## 2. Implementation notes (what changed behind the table)

All changes are additive and in-module — modules 1–17 remain byte-identical to
`main`, `MemoryIndex` is untouched, no new dependencies, no CLI/`explain` change.

- `src/jarvis/kernel/memory_consolidate.py` — reconciliation rewrite (the findings'
  lines moved; the new file is ~419 lines):
  - constructor resolves `self._principal` once; audit appends use it.
  - `gate` Literal gains `any_key_same_source`; `_key_matches` decides on
    source-equality then key-equality or any-key.
  - committed-provenance scan seeds `already_superseded` from
    `provenance.superseded` (memory ids) and `consumed` from `provenance.evidence_ids`
    (trace ids) — the two sets are never confused, so `audit=False` models stay bounded.
    *(This exact split — superseded refs must seed `already_superseded`, not `consumed` —
    was caught by the flipped probe A2 and fixed during reconciliation; it is the
    provenance-side half of FB-M2.3-3.)*
  - new `ContradictionRule.supersede_refine_gap`; `_can_supersede` gates product
    targets on the gap.
  - new `MEMORY_CONSOLIDATE_REJECTED` marker (stream "memory", diagnostic only);
    consume scan honors it; appended with the unified principal.
  - `_normalize` implements the three distinct modes; `_id_refs`/`_evidence_refs`
    guard every provenance read.
  - new `PromotionRule.order` (`log` default | `confidence_desc`).
  - single `log.replay()` pass — no `MemoryIndex.rebuild`.
- `docs/M2_3_KICKOFF.md` — §B (gate values, normalize modes, `supersede_refine_gap`,
  `order`, one-principal), §C (rejected marker + provenance-derived bookkeeping),
  §E.4 (fold-content wording), and §7 (amendment record items 1–9, pending creator
  ratification).
- `tests/review/test_freebuff_redteam_m2_3.py` — the nine marked probes flipped to
  assert the fixed behavior: A2, A3, A4, B1, B2, C1, C2, E1, E2. Regression pins
  A1, A5, C3, D1, E3 unchanged.
- `tests/kernel/test_memory_consolidate.py` — unmodified; all 12 pass unchanged
  (the rewritten semantics are compatible with the ratified kernel suite as written).

## 3. Verification

| Item | Result |
| :--- | :--- |
| `tests/kernel/test_memory_consolidate.py` | 12 passed |
| `tests/review/test_freebuff_redteam_m2_3.py` (flipped) | 14 passed |
| Full suite (`uv run pytest -q`) | **413 passed** (399 committed target + 14 probes) |

## 4. Remaining to closure

1. Creator ratifies `docs/M2_3_KICKOFF.md` §7 amendment record items 1–9 (in
   particular item 4 — product-exclusion default + `supersede_refine_gap`, and
   item 9 — `promote.order` opt-in datum).
2. Commit this reconciliation on `task/m2.3`.
3. Merge `--no-ff` to `main`, replay-verify the merged tree, update
   `project_state.yaml` (`status.m2_memory_os.status: m2_3_completed`), commit +
   push `main`; do not push the branch.