# M2.3 — Consolidation Pipeline — kickoff (PROPOSAL)

**Status:** PROPOSAL — ratified once creator accepts items A–E below.
**Legacy:** M2.1 memory API + episodic trace (DONE, 332→348) · M2.2 embedding +
retrieval seams (DONE, 385 passed; FB-M2.2-3 fold-content ruling).
**Spec anchors:** `MASTER_BUILD_SPEC.md` §84.3 (two-tier consolidation),
§84.4 (verification ladder — rung 1 only), §M2 (named "memory consolidation"),
`docs/M2_KICKOFF.md` rows for M2.3.
**Kernel home (proposal):** `src/jarvis/kernel/memory_consolidate.py`.
**Theme (§84.3, verbatim):** «Not every interaction becomes durable semantic
memory.»

---

## 1. Context

M2.1 gave the two tiers: the raw tier (`memory.trace.recorded` → `MemoryIndex.traces`)
and the verified tier (`memory.write.proposed/verified/committed` →
`MemoryIndex.memories`, gated through the frozen module-10 `DoneGate`). M2.2 added
the ranked retrieval seam over the union, with tier/verification on every hit.

The write-side milestone step is **promotion**: raw episodic traces becoming durable
semantic/procedural memory — deterministically, in-kernel, gated by the SAME frozen
write path, and decided by a **data table (policy), not hardcoded branches**
(`docs/M2_KICKOFF.md` M2.3 row, ratified). M2.3 runs only the **cheap deterministic
rung** of the §84.4 ladder; the semantic verifier and independent verifier are M2.4.

Reads, retrieval, embedding providers, PII, effects, authority, budgets, and
checkpoint/recovery are untouched (their packages). All M2.3 source changes are
additive and in-module; frozen modules (1–17) are never modified.

## 2. Contract items A–E (ratify)

### A. Module `src/jarvis/kernel/memory_consolidate.py`

`MemoryConsolidator(log: EventLog, *, policy: ConsolidationPolicy | None = None,
writer: MemoryWriter | None = None, principal_id: str = "creator")` with
`synchronously` `consolidate() -> ConsolidationResult`. Deterministic, synchronous,
hermetic: **no model calls, no effects, no ambient-state reads, no CLI**. The
pipeline stages are data-driven keys into `ConsolidationPolicy` (§B), not control
branches on memory identity:

1. **Fold** — `MemoryIndex.rebuild(log)` (raw tier = traces, verified tier = memories).
2. **Consume/dedupe** — a trace is already-consolidated if its `event_id` occurs in
   the `evidence_ids` list of any committed memory's provenance (replayed fold order).
   Re-running `consolidate()` on an unchanged log emits **zero events**.
3. **Extract** — group unconsumed traces into candidate clusters by `policy.extract`
   (normalized-content key; e.g. lower/strip/whitespace-collapse). Only clusters with
   `evidence_min` or more members become candidates. Below-threshold traces are
   reported as `skipped`; they are never deleted (append-only) — they simply do not
   promote.
4. **Verify** — each candidate runs the frozen `DoneGate` "memory.write" checks (the
   one rung M1 already implements). A failing candidate is `skipped`, never promoted,
   never raised.
5. **Contradiction resolution** — the candidate's content key is compared against the
   committed fold per `policy.contradiction`. On a DATA-declared conflict (e.g. same
   source, same key, one-way conflicting), the consolidator appends
   `memory.consolidate.superseded` (old committed event_id → candidate) and the
   promoted memory carries the superseded id in provenance. Emits only for resolved
   conflicts.
6. **Promote** — through the injected `MemoryWriter.remember(...)` so the promotion
   runs the EXACT frozen path (`memory.write.proposed` → `verified` → `committed`,
   gate authoritative, `memory_class` from policy, `provenance` carrying
   `evidence_ids` + optional superseded id). Committed payloads stay identical, so
   `MemoryIndex` + `Memory.retrieve`/`recall` consume promotions with zero change.

`ConsolidationResult` (frozen pydantic, extra=forbid): `promoted: list[str]`
(committed memory event_ids), `skipped: list[str]` (+ reason), `superseded:
dict[str, str]` (old→new), `counts` per stage. Determinism: same log, same policy →
identical result (ULID event_ids are outcome keys, not inputs).

### B. `ConsolidationPolicy` — decisioning is DATA

Frozen pydantic `BaseModel` (`extra="forbid"`), fully described decision table:

- `extract: ExtractRule` — `normalize` (**exact = strip only | lower = strip+casefold |
  fold = strip+whitespace-collapse+casefold** — three strictly distinct modes,
  FB-M2.3-7), `content_min_len`, `evidence_min` (min trace members per promoted
  cluster; ≥1).
- `contradiction: ContradictionRule` — `gate` (**same_key_same_source |
  any_key_same_source | disabled** — all three construct and evaluate; the gate
  decides DURING source-equality: same_key_same_source requires identical
  normalized key, any_key_same_source matches any key once source matches,
  FB-M2.3-2), `supersede` (bool), `supersede_evidence_min` (min cluster evidence
  to win a conflict), `supersede_refine_gap: float | None` (**None default:
  consolidation-PRODUCT memories — provenance carries `evidence_ids` — are
  excluded from same-key supersession entirely; a product is superseded only
  when this gap is policy-set AND the candidate's aggregate confidence beats
  the product by ≥ gap — stable facts promote once, then refine on a
  policy-declared gain, never churn, FB-M2.3-4**).
- `promote: PromotionRule` — `memory_class` (semantic | procedural),
  `confidence_floor`, `max_promotions` (`int | None` — cap per run for
  determinism of large folds), `order` (**log | confidence_desc** — which
  candidates fill the cap first, FB-M2.3-9).
- `audit: bool` — emit `memory.consolidate.superseded` when conflicts resolve
  (the `memory.consolidate.rejected` marker has the same audit semantics).
- `principal_id` default `"creator"` (FB-M2.2-7 precedent) — consolidation always
  authors under a caller-declared principal stamped on events it appends.

Additionally (amendment, FB-M2.3-1): the consolidator resolves ONE principal —
the constructor `principal_id` (default: the policy `principal_id`) — and that
principal stamps the promotion chain (`memory.write.*`) AND the audit
events (`memory.consolidate.*`). One consolidation, one principal: the two can
never diverge.

Every branch in the consolidator evaluates one of these data fields — no `if`
dispatches on concrete memory identity, model names, or trace contents. A default
policy is installed and documented in the module docstring (disclosed default, F-C9
file).

### C. Supersession + rejection audit events (stream "memory", additive)

New event type **`memory.consolidate.superseded`** on stream `"memory"`: payload
`{old_event_id, new_event_id, reason, principal_id}`. It is appended ONLY when a
contradiction actually resolves and `policy.audit` is true. It is folded by the
consolidator's own projection (`superseded: dict[old→new]`), **NOT** by
`MemoryIndex` — the M2.1 fold and its digest stay exactly as shipped (FB-M2.2-3
fold-content stability holds: audit lives outside the memories/traces folds).
Promotions leave their own audit trail via the existing `memory.write.*` chain, so
no extra per-promotion event is fabricated.

New event type **`memory.consolidate.rejected`** on stream `"memory"`: payload
`{evidence_ids, reason}`. A promotion whose frozen write-path gate rejects the
passing pre-check is a failed promotion: its evidence ids are recorded ONCE in a
durable marker and never re-attempted, so idempotency ("unchanged log → zero
events") cannot be broken by a seam disagreement (`audit=False` or not, the
marker is always written — a rejection must be sticky to be idempotent,
FB-M2.3-5). The marker is a DIAGNOSTIC audit event like supersede: never folded
by `MemoryIndex`, never in the memories/traces folds.

**Success bookkeeping is derived from committed provenance, never from audit
events** — the authoritative record a later run replays is the promoted memory's
own `provenance.superseded` list. Combined with the product-exclusion rule
(§B), `audit=False` runs stay bounded and can never split-brain (FB-M2.3-3/4).

### D. Integrations (additive only)

- `Memory.consolidate(*, policy=None, principal_id="creator") -> ConsolidationResult`
  on `memory_api.py` — delegates to a consolidator built from the facade's OWN
  `EventLog` (FB-M2.2-4 default) and the module-10 writer. No behavior of
  `recall`/`retrieve`/`get`/`digest` changes.
- No new CLI command (M2.2 item E precedent — `jarvis explain` output and §127.1
  offline parity untouched).

### E. Tests (`tests/kernel/test_memory_consolidate.py`)

Hermetic, offline, deterministic (no dials — ranker seam unused). At minimum:

1. `not_every_interaction_becomes_durable` — a lone low-evidence trace → `skipped`,
   zero events appended.
2. `evidence_min_reached_promotes` — `evidence_min≥2` trace cluster → one committed
   memory via the real `MemoryWriter` chain; fold shows it in `memories`.
3. `idempotent_rerun` — second `consolidate()` on same log → empty result, zero
   new events.
4. `contradiction_supersedes` — conflicting cluster promotes and emits
   `memory.consolidate.superseded`; provenance carries evidence + superseded id;
   `MemoryIndex` fold COMPOSITION (memories/traces keys — fold-input stability,
   FB-M2.2-3 precedent) unchanged by the supersede event (any appended event
   legitimately moves event_count/streams/digest — that is the M2.1 contract).
5. `policy_is_decision_table` — same traces, different `evidence_min`/`confidence_floor`
   policies → different promote/skip sets, no code path change.
6. `gate_failure_skips_not_raises` — candidate failing the `DoneGate` checks is
   reported skipped.
7. `hermeticity` — no `memory.retrieve.reranked`, no model adapter calls, no CLI.

## 3. Scope boundaries (do NOT build in M2.3)

- no semantic verifier / independent verifier (M2.4 §84.4 rungs 2–3)
- no PII detection/redaction/tagging (M2.5)
- no embedding provider calls; consolidation is lexical/deterministic (emb seam → M2.2, no consumer here)
- no filesystem adapter / sandbox / effect execution (M2.6)
- no key-based authority/signatures (M2.8)
- no budget/rate-limit enforcement (M2.9)
- no checkpoint/snapshot/recovery integration (M2.10)
- no new dependencies; no schema or DFA changes to `memory.write.*`; no change to
  frozen modules 1–17; `MemoryIndex` unchanged; no trace deletion (append-only).
- no merging/deleting of raw traces — "consolidate" promotes evidence-bearing traces
  into the verified tier; it never mutates the raw tier.

## 4. Entry conditions (gates)

1. `main` @ `4be72c8`/`d3bafde` (state repair + ledger guard merged), in sync with
   `origin/main`, 387 passed. **CHECKED**.
2. Modules 1–17 frozen; additive-only behind a ratified design — in force.
3. This contract ratified by the creator (accept or refine items A–E).

## 5. Sequencing

1. Ratify items A–E (creator) — including the §B decision-table shape and the
   question "promote-via-`MemoryWriter.remember` vs. dedicated consolidation events"
   (default: reuse the frozen write path).
2. Implement on a task branch (`task/m2.3`): `memory_consolidate.py`,
   `Memory.consolidate`, tests. Run full suite (387 baseline + new).
3. Adversarial pass (Freebuff) + independent verify (Antigravity) on the
   consolidation/decision-table contracts.
4. Reconcile findings; flip pins; full suite green.
5. Merge to `main` (`--no-ff`), record in `project_state.yaml`, push, do not push
   the branch.

---
## 6. Ratification decision (creator)

- [x] **Ratify A–E as written — 2026-09-19 (creator).** R1: promote via the frozen
  `MemoryWriter` path — ACCEPTED. R2: supersession audit events stay OUTSIDE
  `MemoryIndex` folds — ACCEPTED (fold-content stability, FB-M2.2-3 precedent).
- [ ] Amend (list changes) → re-propose
- [ ] Hold

**Rulings requested before implementation:** (R1) promote via the frozen
`MemoryWriter` path (recommended) vs. dedicated `memory.consolidate.*` events;
(R2) accept supersession audit events being excluded from `MemoryIndex` folds
(recommended) vs. extend `MemoryIndex`.

## 7. Amendment record — dual-verification reconciliation (2026-09-19)

Freebuff red-team (FB-M2.3-1..11) and Antigravity audit (F-M2.3-1..11) both
returned `M2_3_RECONCILIATION_REQUIRED` against `c78f406`. The reconciliation
(landed on `task/m2.3`, evidence in `docs/M2_3_RECONCILIATION.md`) amends the
ratified contract as follows:

1. **One consolidation, one principal** (FB-M2.3-1, F-M2.3-11): constructor
   `principal_id` (default `policy.principal_id`) stamps the write chain AND the
   audit events. Contract §B amended.
2. **`any_key_same_source` gate restored** (FB-M2.3-2): all three declared gates
   construct and evaluate. Contract §B amended.
3. **Success bookkeeping from committed provenance** (FB-M2.3-3, F-M2.3-2): the
   already-superseded set is derived from each committed memory's own
   `provenance.superseded` (persisted in the authoritative record), never from
   audit events — `audit=False` cannot split-brain. Contract §C amended.
4. **Product-exclusion + `supersede_refine_gap`** (FB-M2.3-4): consolidation-product
   memories are excluded from same-key supersession by default; products are
   superseded only on a policy-declared confidence gain. Contract §B amended.
5. **Sticky rejection marker** (FB-M2.3-5): new `memory.consolidate.rejected`
   diagnostic event records a failed promotion once; evidence is never
   re-attempted. Contract §C amended.
6. **Fold-content wording** (FB-M2.3-6, F-M2.3-6): contract §E.4 rewording per the
   FB-M2.2-3 precedent — fold inputs stable; digest/event_count move with any
   appended event.
7. **Distinct normalize modes** (FB-M2.3-7): exact = strip only, lower =
   strip+casefold, fold = strip+collapse+casefold. Contract §B amended.
8. **Robust provenance shape** (FB-M2.3-8a/b, F-M2.3-4): `evidence_ids`/`superseded`
   reference handling can never raise untyped; a string is one reference, other
   non-sequence shapes are ignored.
9. **`promote.order` (log | confidence_desc)** (FB-M2.3-9): which candidates fill a
   `max_promotions` cap. Contract §B amended.

- [ ] **Ratify amendment record items 1–9** (creator) — see
  `docs/M2_3_RECONCILIATION.md` for evidence and decision rationale.