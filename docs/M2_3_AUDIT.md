# M2.3 — Consolidation Pipeline — Independent Audit (Antigravity)

**Role:** Antigravity — independent engineering & quality reviewer (VERIFIER).
**Target:** branch `task/m2.3` @ **`c78f406`** (parent `main` @ `d3bafde`).
**Date:** 2026-09-19.
**Method:** entirely read-only over `src/`, `tests/`, `docs/`, `project_state.yaml`, `uv.lock` (re-derived on disk; no quoted value trusted). One write: this report. No commits.

---

## Verdict

# M2_3_RECONCILIATION_REQUIRED

The deterministic core is sound and independently confirmed — additive-only diff, frozen modules 1–17
byte-identical, hermetic (no model/network/effects/ambient reads), data-driven branches, promotion through
the frozen `MemoryWriter` chain, fold-content stability (R2), no ghost hashes, 399 passed on the committed
target — but **seven MEDIUM contract-fidelity gaps** sit directly on the package's own ratified contract
items A–E, and the milestone's own sequencing (adversarial pass → independent verify → **reconcile** →
flip pins → merge) is not yet complete. No CRITICAL/HIGH findings.

- **Suite counts verified:** 399 passed (committed target, `c78f406`); 12/12 consolidation tests, stable
  across two consecutive runs; 413 passed (workspace incl. red-team probes, after probe finalization).
- **Step-1 diff confirmation (additive-only):** CONFIRMED — see §A below.

---

## 1. Preconditions re-derived (not trusted)

| Item | Observed |
| :--- | :--- |
| HEAD | `c78f406765d881eda6dcef1bb5aa42892677bfe7` on `task/m2.3` |
| Parent | `d3bafde51835eeefd030845b17aef02cd7e866dd` (= `git rev-parse main` = `origin/main`) — in sync |
| Working tree at review start | clean at `HEAD` |
| `git diff main --stat` | 4 files: `docs/M2_3_KICKOFF.md` (A), `src/jarvis/kernel/memory_api.py` (+21), `src/jarvis/kernel/memory_consolidate.py` (A, 287 L), `tests/kernel/test_memory_consolidate.py` (A, 12 tests) |
| Spec anchors | `MASTER_BUILD_SPEC.md:3242-3264` (§84.3 two-tier), `:3266-3278` (§84.4), `:4957-4980` (§M2, "consolidation pipeline" build item) — verified verbatim |
| Contract | `docs/M2_3_KICKOFF.md` items A–E, ratified 2026-09-19 with rulings R1 (promote via frozen writer) / R2 (supersede outside MemoryIndex folds) |

---

## 2. Mandated checks 1–8

### ✅ Check 1 — Additive-only / frozen modules: PASS (CONFIRMED)
`git diff main -- src/` yields exactly two files:
- `src/jarvis/kernel/memory_consolidate.py` — new (287 lines).
- `src/jarvis/kernel/memory_api.py` — one added import (`memory_api.py:22`) and one added method
  `Memory.consolidate` (`memory_api.py:115-133`). No other hunk.

Every other file under `src/` is byte-identical to `main` (verified per-file for `memory_index.py`,
`memory_write.py`, `done_gate.py`, `event_log.py`, `registry.py`, `memory_trace.py`,
`memory_projection.py`, and by the empty diff of the whole tree). `pyproject.toml` and `uv.lock` show a
**zero-line diff** vs `main` → no new dependencies. No file outside the four listed differs from `main`.

### ✅ Check 2 — Determinism & hermeticity: PASS
Read `memory_consolidate.py` fully (287 lines). Imports (`:34-43`): `re`, `typing`, `pydantic`,
`.done_gate`, `.event_log`, `.memory_index`, `.memory_write`, `.registry` — confirmed by AST scan; no
`os`/`sys`/`datetime`/`time`/`random`/`uuid`/`socket`/`http*`/asyncio/threading/subprocess, and no
`environ` anywhere in the module. No model, no network, no effects, no filesystem read beyond the injected
`EventLog`; no dispatch on clock or ULID (ULIDs and timestamps are stamped onto **outcome** events only —
`event_log.py:202-204` — and never read back into a decision). All iteration is over `log.replay()` /
`MemoryIndex.rebuild` (seq-ordered, integrity-verified, deterministic). Two replays are made per
consolidation (cost, not correctness — §F-M2.3-10).

### ✅ Check 3 — Idempotency & dedupe (default path): PASS; conditional on provenance/gate shape (→ findings)
- Consume rule implemented as ratified: a trace is already-consolidated iff its `event_id` is in the
  `evidence_ids` of a committed memory's provenance (`memory_consolidate.py:129-134`).
- Independent replay checks (read-only, temp sqlite, `uv run python -`): re-running `consolidate()` on an
  unchanged log appended **zero events**; a lone follow-up trace was the only unconsumed item and was
  reported `below_evidence_min`; cluster promotion via 2 identical traces produced
  `evidence_ids == [t1, t2]`.
- Edge-path weaknesses confirmed (dedupe integrity is not robust to malformed provenance shapes, and
  re-run-zero-events is not robust to an injected gate mismatch) → **F-M2.3-3**, **F-M2.3-4**.

### ✅ Check 4 — Decisioning is DATA: PASS (with contract-surface drifts → F-M2.3-1, F-M2.3-8, F-M2.3-9)
Every branch in `consolidate()` evaluates a `ConsolidationPolicy` field (`extract.content_min_len`,
`extract.evidence_min`, `promote.max_promotions`, `promote.confidence_floor`, `contradiction.gate`,
`contradiction.supersede`, `contradiction.supersede_evidence_min`, `policy.audit`). Content flows into
decisions **only** through the policy-driven normalization key `_normalize` (`:50-52,149,222-225`). There is
no dispatch on concrete memory identity, model names, or content equality. Drifts: the ratified decision
table declares 3 `contradiction.gate` values but the `Literal` ships 2; `normalize` modes collapse; the
`max_promotions` winner set is chosen by log position, not a policy datum (see findings).

### ✅ Check 5 — Promotion path integrity: PASS
Promotion goes through `self._writer.remember(...)` (`memory_consolidate.py:239-248`) — the frozen module-10
chain `proposed → verified → committed`. Independent replay verified:
- committed event id == `result.event_ids[-1]` (contract A: "committed memory event_ids");
- causality: `committed.cause = verified.id`, `verified.cause = proposed.id`, correlation root = proposed id
  (`verified.correlation_id == committed.correlation_id == proposed.event_id`);
- failure handling: `result.status != "committed"` → members skipped as `promotion_rejected`
  (`:249-252`), nothing promoted, no raise (12-test suite + my replay); non-stickiness flaw → **F-M2.3-3**.

### ✅ Check 6 — Supersession audit isolation (R2): PASS
`MemoryIndex._from_events` folds **only** `memory.write.committed` and `memory.trace.recorded`
(`memory_index.py:56-61`); `memory.consolidate.superseded` events are invisible to the folds.
`memory_index.py` is byte-identical to `main`. Independent replay: after a supersession,
`len(idx.memories) == 2`, supersede event id is in neither fold, `provenance.superseded == [old_id]`,
`result.superseded == {old_id: new_id}`. Metadata (`event_count`, `streams["memory"]`) legitimately bumps
**for any appended event** — same M2.1 semantics, consistent with the FB-M2.2-3 fold-content-stability
ruling (M2_2_RECONCILIATION.md:20). The ratified E.4 wording "digest unchanged" is imprecise → **F-M2.3-7**.

### ✅ Check 7 — Test determinism: PASS (for the committed target; see process note F-M2.3-11)
- `uv run pytest -q` on the committed target (untracked red-team probes excluded): **399 passed** in 20.21s,
  0 failures/timeouts — exactly the stated claim.
- `tests/kernel/test_memory_consolidate.py` run twice: **12 passed / 12 passed** (1.56s, 2.46s) — stable.
- The 12 tests cover: lone-trace skip, evidence-min promotion through the frozen writer, idempotent rerun
  (zero new events), contradiction supersede + audit payload, fold isolation, policy-as-decision-table,
  gate-failure skip, confidence-floor gate, facade with own log, facade requiring EventLog, follow-up lone
  trace no-repromote, contradiction no-win keeps existing memory.

### ✅ Check 8 — State/docs truthfulness: PASS
- `docs/M2_3_KICKOFF.md` §4 ("main @ `4be72c8`/`d3bafde`, in sync with origin/main, 387 passed, CHECKED"):
  both hashes resolve (`4be72c8…`, `d3bafde…`); `origin/main == main == d3bafde`; the **387** baseline is
  consistent by construction — `main @ d3bafde` = 385 (e417de3 M2.2 merge) + 2 ledger-guard tests
  (`tests/test_project_state.py`, added by d3bafde), and branch adds exactly 12 → 387 + 12 = 399 (empirical).
- No ghost hashes in the kickoff (every 7–40 hex token resolves successfully).
- Historical counts in the kickoff header reconcile: M2.1 "332→348" (M2_2_AUDIT.md:23), M2.2 "385 passed"
  (M2_2_RECONCILIATION.md:7), both truthful.
- Commit `c78f406` message claims "12 tests, 399 passed" — TRUE (empirically confirmed).
- `project_state.yaml` still records `m2_2_completed` with next-step "kickoff M2.3": expected pre-merge
  (sequencing step 5 updates state at merge) — INFO, not a defect.

---

## 3. Findings

| ID | Severity | Location | Summary |
| :-- | :-- | :--- | :--- |
| F-M2.3-1 | MEDIUM | `memory_consolidate.py:66` vs `docs/M2_3_KICKOFF.md:78-82` | Ratified decision table (item B) declares `contradiction.gate in {same_key_same_source \| any_key_same_source \| disabled}`; shipped `Literal` accepts only `same_key_same_source \| disabled`. A policy author following the ratified contract gets `ValidationError`. The "decisioning is DATA" surface is silently smaller than ratified. (= Freebuff FB-M2.3-2) |
| F-M2.3-2 | MEDIUM | `memory_consolidate.py:263,269` vs `:117-119` | One consolidation credits two principals: the `memory.write.*` chain is stamped with the caller-declared constructor principal (`principal_id or policy.principal_id`, e.g. "drone"), but the `memory.consolidate.superseded` audit event is hard-stamped `policy.principal_id` ("creator"). Violates item B "consolidation always authors under a caller-declared principal stamped on events it appends". Additive fix: use the same effective principal for the audit append. (= FB-M2.3-1) |
| F-M2.3-3 | MEDIUM | `memory_consolidate.py:202-213` vs `:239-252` | "Re-running `consolidate()` on an unchanged log emits zero events" (item A) is only default-path true. The gate is evaluated twice — consolidator's `self._gate` pre-check, then the injected `MemoryWriter`'s own gate. On divergence (both seams public/injectable), each rerun re-appends `proposed → verified → rejected` forever because a rejection commits nothing and no evidence enters `evidence_ids`. (= FB-M2.3-5) |
| F-M2.3-4 | MEDIUM | `memory_consolidate.py:129-134`; reachable via public seam `memory_write.py:86-94` | Provenance-shape abuse defeats consume/dedupe. `evidence_ids` is iterated with zero shape check: a STRING is scanned char-by-char (referenced trace never consumed → duplicate promotion of a raw trace already referenced by a committed memory); an INT raises a raw `TypeError` from the public `Memory.consolidate` seam — a permanent, untyped crash on every later run of that log. (= FB-M2.3-8) |
| F-M2.3-5 | MEDIUM | `memory_consolidate.py:135-140,246,256-274` | `already_superseded` is derived only from `memory.consolidate.superseded` audit events, which are appended only when `policy.audit=True`. In `audit=False` mode supersession still happens structurally (provenance), but the bookkeeping is empty, so every later generation re-collects ALL prior generations: `provenance.superseded` grows `[g0]`, `[g0,g1]`, `[g0,g1,g2]` … unbounded. The module's two records of supersession drift apart. (= FB-M2.3-3) |
| F-M2.3-6 | MEDIUM | `memory_consolidate.py:215-234` | A consolidation PRODUCT is itself a fresh collision target. Run-2 collides the run-1 promotion N1 (identical key+source) and supersedes it by N2; run-3 supersedes N2 by N3 … Identical stable content slides the "final" memory forward forever, one supersede event + one re-promotion per evidence batch. Only the original pre-consolidation memory is pinned. Contract-conformant reading exists ("same source, same key, one-way conflicting") → needs a creator ruling, not just a code flip. (= FB-M2.3-4) |
| F-M2.3-7 | MEDIUM | `docs/M2_3_KICKOFF.md:124` (item E test 4 wording) vs shipped `memory_index.py:56-72`, `memory_consolidate.py:256-272` | Ratified E.4 wording "`MemoryIndex` digest unchanged by the supersede event" is not what the fold ships. R2 holds (fold CONTENT stable — verified), but the audit event lands on stream `"memory"`, so `event_count` / `streams["memory"]` / `digest()` move per resolved conflict. Same shape as FB-M2.2-3; the accepted precedent was a contract-wording amendment ("digest inputs" → "fold inputs"). Needs the same ruling re-applied; no frozen-module change permitted. (= FB-M2.3-6) |
| F-M2.3-8 | LOW | `memory_consolidate.py:50-52,58` | `normalize` modes are not distinct: the whitespace collapse runs before branching, so `"exact"` is not byte-exact (internal whitespace variants cluster together) and `"lower"` ≡ `"fold"`. Decision surface exposes three values for two behaviors. (= FB-M2.3-7) |
| F-M2.3-9 | LOW | `memory_consolidate.py:181-188` | `max_promotions` is applied to the FIRST clusters in replay order, before confidence/gate/contradiction are evaluated: a 0.05-confidence early cluster is promoted while a 0.99-confidence later cluster is capped. Deterministic, but the winner set is decided by log insertion position, not by any policy datum ("decisioning is DATA" stops one step short). Cap boundary itself correct (cap=1 → exactly 1; None → all). (= FB-M2.3-9) |
| F-M2.3-10 | INFO | `memory_consolidate.py:205,239-241,123,136` | (a) The committed memory's raw content is `members[-1]` — the last trace's verbatim text in log order, not a policy datum; document or pick deliberately. (b) Perf: the log is fully replayed twice per `consolidate()` (rebuild + supersede scan), both integrity-verified; reuse one replay on large logs. (= FB-M2.3-10/11) |
| F-M2.3-11 | LOW | working tree (process) | The freeze state was NOT stable during the review window: `tests/review/test_freebuff_redteam_m2_3.py` and `docs/M2_3_REDTEAM_FB.md` (Freebuff red-team deliverables) landed **untracked, mid-audit** (probe file was mid-edit while observed; my first full-workspace `uv run pytest` collected 413 with **3 failures** from a transient probe revision asserting flipped targets). Final probe revision passes (413). Committed-target count (399) was unaffected and remains reproducible (re-run twice). Independent re-verification of the merged milestone should re-freeze the tree at the chosen commit and ignore the adversarial worktree. |

Severity summary: **0 CRITICAL · 0 HIGH · 7 MEDIUM · 3 LOW · 1 INFO.**

### Independent-pass list (held under verification)
- Additive-only diff; frozen modules 1–17 byte-identical; CLI/`explain` untouched; no new dependencies.
- Hermeticity: no model/network/effects/ambient-state reads; imports restricted; clock/ULID are outcomes only.
- Default-path idempotency: unchanged-log rerun appends zero events (multiple independent replays).
- Promotion via the frozen `MemoryWriter.remember`; committed id == `result.event_ids[-1]`; causal chain + correlation root correct.
- Fold-content stability (R2): supersede events never enter `memories`/`traces` folds.
- Determinism: 399 passed, no failures/timeouts; consolidation file stable across two consecutive runs.
- Docs/state truthfulness: all kickoff hashes resolve; all suite counts reconcile (332→348→385→387 baseline→399); "12 tests, 399 passed" is factually true.

---

## 4. Bottom line

The M2.3 implementation is a disciplined, additive, deterministic consolidation pipeline whose committed
state matches every numeric and structural claim in its own kickoff and commit message. It is **not yet
merge-ready**: the seven MEDIUM findings (each independently confirmed against the committed code, and
concurrent with Freebuff's FB-M2.3-1..9) touch the package's own ratified contract — the declared decision
table, caller-principal authoring, unconditional zero-event rerun, dedupe integrity on a public seam,
supersession boundedness, and the E.4 digest wording (which needs the FB-M2.2-3 ruling re-applied). All
resolutions are additive and in-module; none require touching frozen modules 1–17.

**Verdict: M2_3_RECONCILIATION_REQUIRED.** Next step: reconcile F-M2.3-1..11 (creator ruling on F-M2.3-6),
flip the `# FLIPS ON FIX` probe pins, re-run the full suite, then merge per sequencing step 5.