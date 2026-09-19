# Freebuff — Adversarial Review Report (M2.3)

## Milestone 2 · Package M2.3 — Consolidated Promotion Pipeline

**Reviewer:** Freebuff (adversarial red-team; JARVIS 2.0)
**Target:** branch `task/m2.3` @ **`c78f406`** (`M2.3: deterministic consolidation pipeline …`)
**Parent:** `main` @ `d3bafde`
**Date:** 2026-09-19
**Status of findings:** **PROPOSALS** — not accepted architecture. **No `src/` file was modified.** Working
tree untouched except this report and the probe file.
**Baseline:** 399 passed · **with evidence probes: 413 passed** (14 probes added, all PASS).
**Verdict:** **M2_3_RECONCILIATION_REQUIRED** — no CRITICAL/HIGH, but seven MEDIUM findings sit directly on
the package's four promises: principal-stamp consistency (B), the full declared decision table (B), bounded
idempotency on rejected promotions (A/E), dedupe robustness to provenance shape (A), supersession chain
boundedness (A), and the freshly-ratified E.4 digest wording (C/FB-M2.2-3 precedent).

---

## 1. Preconditions (reproduced, not trusted)

| Check | Observed |
| :--- | :--- |
| Branch / HEAD | `task/m2.3` @ `c78f406` (`M2.3: deterministic consolidation pipeline…`) |
| Parent / diff scope | `git diff main --stat` = `docs/M2_3_KICKOFF.md`, `memory_api.py` (+21 additive), `memory_consolidate.py` (new), `tests/kernel/test_memory_consolidate.py` (new). `git diff main -- pyproject.toml src/jarvis/cli.py src/jarvis/kernel/explain.py` = empty → **frozen modules 1–17 byte-identical**, no new deps, no CLI change. |
| Baseline suite | `399 passed in 22.76s` — matches prompt |
| Probes | `tests/review/test_freebuff_redteam_m2_3.py` — **14 passed in 1.94s** |
| Full suite w/ probes | `413 passed in 20.59s` (**+14** vs baseline) |
| Contract read | `docs/M2_3_KICKOFF.md` (items A–E, ratified; rulings R1/R2), `docs/M2_KICKOFF.md` M2.3 row, `MASTER_BUILD_SPEC.md` §84.3/§84.4 |
| Predecessor seams | `memory_index.py`, `memory_trace.py`, `memory_write.py`, `done_gate.py`, `memory_retrieval.py`, `memory_api.py` re-read from disk |

---

## 2. Findings

### FB-M2.3-1 — MEDIUM — One consolidation, two principals: promotion chain vs. supersede audit
**Location:** `src/jarvis/kernel/memory_consolidate.py:117-119` (writer stamped `principal_id or
policy.principal_id`) vs `:261` (supersede audit event stamped hard `policy.principal_id`); surfaced again by
the facade `memory_api.py:131-133` (`Memory.consolidate(principal_id=…)` forwards only to the constructor).
**Failure mode:** `MemoryConsolidator(log, principal_id="drone")` stamps the `memory.write.proposed /
verified / committed` chain `"drone"` but the `memory.consolidate.superseded` event `"creator"` (the policy
default). The frozen-path writers (module 10, M2.1 trace writer) all take a caller-defined principal; the
constructor's `principal_id` is the caller-declared authoring principal per kickoff item B
(FB-M2.2-7 precedent). The audit trail therefore re-authors the caller — a provenance lie on the very event
that records the caller's decision to supersede.
**Evidence:** scratch replay (and `test_e1_principal_stamp_split_between_write_and_audit`,
`test_e2_facade_consolidate_principal_split`, both PASS at `c78f406`): `drone_writes == 3`,
`audit_principals == {"creator"}` — with 0.5- and 0.95-confidence traces seeding a real supersession.
**Severity:** MEDIUM.
**Resolution (additive):** the audit append must stamp the SAME effective principal as the writer,
i.e. `principal_id or policy.principal_id`. FLIPS pins: `test_e1`, `test_e2`.

### FB-M2.3-2 — MEDIUM — Ratified contract item B declares three gate values; the schema ships two
**Location:** `src/jarvis/kernel/memory_consolidate.py:66` —
`gate: Literal["same_key_same_source", "disabled"]` vs `docs/M2_3_KICKOFF.md:78-82` —
`gate (same_key_same_source | any_key_same_source | disabled)` (ratified verbatim).
**Failure mode:** the DATA decision table cannot express `any_key_same_source`. Constructing
`ConsolidationPolicy(contradiction={"gate": "any_key_same_source"})` raises `ValidationError`
(`literal_error`) — the decision surface is silently smaller than the contract that was ratified, so a
policy author following the kickoff gets a schema error instead of a decision.
**Evidence:** `test_b1_any_key_same_source_rejected_by_schema` (PASS at `c78f406` —
pins the rejection).
**Severity:** MEDIUM (contract-fidelity gap in the central "decisioning is DATA" table).
**Resolution:** restore the third gate value and its (data-driven) evaluation branch under
`promote`/`contradiction`; extend the fold. FLIPS pin: `test_b1`.

### FB-M2.3-3 — MEDIUM — `audit=False` splits supersession bookkeeping; provenance.superseded grows unbounded
**Location:** `src/jarvis/kernel/memory_consolidate.py:135-140` (`already_superseded` derived ONLY from
`memory.consolidate.superseded` audit events) but `:246` (supersession also recorded structurally in the
committed memory's `provenance.superseded`).
**Failure mode:** with `policy.audit=False` no audit event is ever appended, so `already_superseded` stays
empty while supersession itself still happens. Every later generation's contradiction scan therefore
re-collects ALL prior generations: for a stable fact with steady evidence, `provenance.superseded` grows
`[g0]`, `[g0,g1]`, `[g0,g1,g2]` … per promotion. Provenance is the actual record of supersession; the
dedupe source of truth is an event stream that silently does not exist in the very mode that disables it.
**Evidence:** `test_a2_audit_false_supersession_chain_grows` (PASS at `c78f406`): three generations →
superseded lists of length 1, 2, 3.
**Severity:** MEDIUM (unbounded provenance growth; the module's own two records of supersession drift apart).
**Resolution:** read the already-superseded set from committed provenance (the authoritative record), or
always append the audit event and let `audit` control only its visibility/consumption. FLIPS pin:
`test_a2`.

### FB-M2.3-4 — MEDIUM — A promotion is itself a fresh collision target: stable facts self-supersede forever
**Location:** `src/jarvis/kernel/memory_consolidate.py:215-234` — the contradiction scan iterates
`idx.memories` and excludes only `already_superseded` ids; superseded OLD memories are excluded but a run-1
PROMOTION is not.
**Failure mode:** run 1 supersedes O→N1 (content X). Run 2 receives two more traces of the same content X:
N1 collides with the candidate (same key, same source), evidence ≥ `supersede_evidence_min` → N1 superseded
by N2. Run 3 supersedes N2 by N3 — and so on. Identical, never-changing content emits one
`memory.consolidate.superseded` event and one supersession per evidence batch, sliding the "final" memory
forward forever. Only the ORIGINAL pre-consolidation memory is pinned; the consolidator's own output has no
"product of consolidation" marker to stop the chain.
**Evidence:** `test_a3_third_run_supersedes_own_promotion` (PASS at `c78f406`): run2 supersedes
`[n1]` — the run-1 promotion, not the original old id.
**Severity:** MEDIUM (perpetual churn on stable beliefs; log growth proportional to evidence traffic).
**Resolution:** mark consolidation-product memories (e.g. provenance flag) and exclude them from
same-key collision, or only engage supersession on a real content-conflict signal rather than key equality
alone. FLIPS pin: `test_a3`.

### FB-M2.3-5 — MEDIUM — Rejected promotions are not sticky: rerun re-appends forever (idempotency broken via the injected-writer seam)
**Location:** `src/jarvis/kernel/memory_consolidate.py:202-213` (consolidator gate pre-check) vs `:239-252`
(the injected `MemoryWriter.remember` decision, `:249-252` handles rejection by skipping).
**Failure mode:** the consolidate-time gate is evaluated TWICE against two possibly-different gate
instances — the consolidator's `self._gate` (constructor) decides the candidate, then the writer's OWN gate
decides the commit. If they diverge (both are public, injectable seams; the writer takes `gate=`), the
promotion can fail after the pre-check passed. Because a rejection commits nothing, no trace id ever enters
`evidence_ids`, so the SAME candidate re-evaluates on every rerun and re-appends
`memory.write.proposed → verified → rejected` each time: unbounded log growth and a direct violation of
E.3 ("re-running consolidate() on an unchanged log emits zero events"). With default wiring the two gates
coincide and the path is latent; it is reachable the moment a caller injects a writer.
**Evidence:** `test_a4_rejected_promotion_reruns_appending_events` (PASS at `c78f406`): run2 appends the
same rejected chain again; `len(after_run2) > len(after_run1)`.
**Severity:** MEDIUM (idempotency is conditional on gate-coincidence across two seams, not guaranteed).
**Resolution:** drive the writer from the SINGLE consolidator gate decision (no double pre-check), or persist
a durable rejection marker the consume scan honors (e.g. a `memory.consolidate.skipped` marker event keyed
on evidence ids) so reruns are no-ops. FLIPS pin: `test_a4`.

### FB-M2.3-6 — MEDIUM — Ratified E.4 wording "MemoryIndex digest unchanged by the supersede event" is not what the fold delivers (fold content is stable; metadata moves)
**Location:** `docs/M2_3_KICKOFF.md:66-68` (item E test 4 wording) vs `src/jarvis/kernel/memory_index.py`
`streams`/`event_count` over the FULL replay (`:56-68`) and `digest()` hashing the whole projection state
(`:70-72`); the audit event is appended to stream `"memory"` at `memory_consolidate.py:256-272`.
**Failure mode:** ruling R2 holds — the supersede event never enters `memories`/`traces` (verified:
`len(post.memories)==2`, `set(post.traces)=={t1,t2}`). But it DOES land on stream `"memory"`, so
`event_count` and `streams["memory"]` rise with every resolved conflict (`streams["memory"] ==` the audit
event's `stream_seq`), and because the M2.1 digest hashes those fields, `MemoryIndex.digest()` moves. The
freshly-ratified E.4 promise as written is therefore unmet. This is the exact FB-M2.2-3 shape, whose
accepted ruling was a contract amendment ("digest inputs unchanged" → "fold inputs unchanged"). M2.3 needs
the same ruling; no index code may change (frozen).
**Evidence:** `test_d1_superseded_event_folds_stable_but_digest_moves` (PASS at `c78f406`):
`post.event_count == pre.event_count + 4`; audit stream seq == `streams["memory"]`; digest deterministic
across rebuilds.
**Severity:** MEDIUM (contract-vs-code drift on the digest guarantee; recovered/diff consumers see a moving
digest per consolidation).
**Resolution (creator ruling, no frozen-module changes):** amend item E.4/C wording to "fold inputs
unchanged / memories-traces folds unchanged" exactly as M2.2 was amended, and document that event_count /
streams / digest move with every appended event. Not a flip.

### FB-M2.3-7 — LOW — `normalize` modes are not distinct: "exact" is not byte-exact and "lower" ≡ "fold"
**Location:** `src/jarvis/kernel/memory_consolidate.py:50-52` (`_normalize`) with `:58` /
`:76` (declared modes `exact | lower | fold`).
**Failure mode:** `_normalize` ALWAYS runs `WHITESPACE.sub(" ", content.strip())` before branching, so
`"exact"` still collapses whitespace (two contents differing only in internal whitespace cluster together
under the "exact" key) and the `"lower"` and `"fold"` branches return the identical string. The decision
table exposes three values for two behaviors, and the strongest-sounding mode is not exact — the
extract-key semantics a policy author reads off the data field differ from the ones shipped.
**Evidence:** `test_b2_normalize_modes_not_distinct` (PASS at `c78f406`):
`_normalize("A  B","exact") == _normalize("A B","exact")` and
`_normalize("A B","lower") == _normalize("A B","fold")`.
**Severity:** LOW.
**Resolution:** exact → byte-exact (strip only); lower → casefold only; fold → collapse + lower; regression
pins updated. FLIPS pins: `test_b2`.

### FB-M2.3-8 — MEDIUM — Provenance shape abuse defeats consume/dedupe: string scans character-wise (duplicate promotion) and int crashes consolidate with a raw TypeError
**Location:** `src/jarvis/kernel/memory_consolidate.py:129-134` — `for evidence_id in
(payload.get("provenance") or {}).get("evidence_ids", [])` iterates the value with zero shape validation;
the value arrives verbatim through the public `MemoryWriter.remember` seam (`memory_write.py:86-94`,
provenance is `dict(provenance or {})` with no sub-schema).
**Failure mode:** a committed memory whose `provenance["evidence_ids"]` is a STRING is iterated
character-by-character — none of the referenced trace ids are consumed, the referenced raw trace stays
eligible, and `consolidate()` re-promotes it into a duplicate durable memory (the referencing memory's own
provenance fails to "prove" it). A non-list/non-string value (e.g. int) raises a RAW `TypeError:
'int' object is not iterable` from the public `Memory.consolidate` seam, mid-pipeline, before any event is
appended — a permanent, untyped crash on every subsequent run of that log. The "a trace is
already-consolidated iff its id is in evidence_ids" predicate is only as sound as whichever caller wrote the
provenance.
**Evidence:** `test_c1_string_evidence_ids_disables_dedupe` (PASS at `c78f406`): duplicate promotion of the
referenced trace; `test_c2_int_evidence_ids_crashes_consolidate` (PASS): `TypeError` escapes.
**Severity:** MEDIUM (typed-failure discipline + dedupe integrity on a caller-reachable seam).
**Resolution (additive, no frozen change):** validate `evidence_ids` shape at the consume seam (accept
lists/tuples/single reference; reject other shapes with a typed resolve, or treat a malformed value as
"this memory provably consumed nothing" only after a typed warning), and reject malformed provenance at the
integrations boundary. FLIPS pins: `test_c1`, `test_c2`.

### FB-M2.3-9 — LOW — `max_promotions` winners are chosen by log position, not by any policy datum
**Location:** `src/jarvis/kernel/memory_consolidate.py:181-188` — the cap check runs BEFORE
confidence/gate/contradiction, in `candidates` = log-insertion order.
**Failure mode:** the cap is applied to the FIRST clusters in replay order. A 0.05-confidence cluster placed
earlier in the log is promoted while a 0.99-confidence cluster placed later is capped
(`promotion_cap`) — the winner set is decided by insertion position, which is an input property the policy
never names. Deterministic, but "decisioning is DATA" stops one step short: no ordering/priority datum
exists for cap allocation.
**Evidence:** `test_a5_max_promotions_boundary_and_order_winners` (PASS at `c78f406`): cap=1 promotes the
beige/0.05 cluster and caps launch-window/0.99; cap boundary pin held (`cap=1 → 1`, `None → 2`).
**Severity:** LOW (determinism intact; strength-blind winner selection).
**Resolution (additive, optional):** sort candidates by a policy-declared priority (e.g. min confidence
desc) before applying the cap, or document first-come-first-served as the disclosed default. No flip
recommended unless ordering is specified.

### FB-M2.3-10 — INFO — The committed memory's content is the LAST trace's raw text (log order), not a policy datum
**Location:** `src/jarvis/kernel/memory_consolidate.py:205` and `:239-241` — `members[-1]["content"]`.
**Failure mode / evidence:** cluster members normalize to the same key but may carry different raw text
(e.g. double-space variants); the promoted payload stores `members[-1]` — the last-appended trace's verbatim
content, chosen by log position. Per-log deterministic and internally consistent
(`test_e3_committed_content_is_last_trace_in_log_order`, PASS), but the association "which raw variant
becomes durable" is decided by event order, not by the policy.
**Severity:** INFO (documented behavior; no action without a creator preference).

### FB-M2.3-11 — INFO — The log is fully replayed twice per consolidate (perf, not correctness)
**Location:** `src/jarvis/kernel/memory_consolidate.py:123` (`MemoryIndex.rebuild(log)` = replay 1) and
`:136` (`self._log.replay()` = replay 2). Both verify the hash chain (NAT-04) so the duplicate is only
cost; on a large log the already_superseded scan could reuse the rebuild's event list.
**Severity:** INFO.

---

## 3. Attack-surface sweep — what held (adversarial PASS pins)

These are kept as regression pins in `tests/review/test_freebuff_redteam_m2_3.py`:

| Surface probed | Probe(s) | Outcome at `c78f406` |
| :--- | :--- | :--- |
| Determinism: replay-twice identical digest; re-run appends zero events (happy path) | A1 | PASS |
| Cap boundary: `max_promotions=1` → exactly 1; `None` → all | A5 | PASS |
| `evidence_min=1` promotes a lone trace; rerun zero events | C3 (with confidence-floor == boundary) | PASS |
| Confidence floor equality boundary (conf == floor → promote) | C3 | PASS |
| Fold-content stability: supersede events never enter memories/traces folds | D1 | PASS (R2 honored; metadata moves — FB-M2.3-6) |
| `memory.consolidate.superseded` event payload sanity (old/new/reason/principal) | D1 | PASS |
| Frozen modules 1–17 byte-identical vs `main` | git diff | PASS (no CLI/explain/deps drift) |
| No model calls / hermetic / synchronous sync path | whole module review + A1 | PASS (no seams dialled; no clock/ULID on decisions) |

## 4. Evidence retained

- `tests/review/test_freebuff_redteam_m2_3.py` — 14 behavioral probes. Assertions pinning current behavior
  that a corrective fix is expected to flip carry `# FLIPS ON FIX` — FB-M2.3-1 (`E1/E2`), FB-M2.3-2 (`B1`),
  FB-M2.3-3 (`A2`), FB-M2.3-4 (`A3`), FB-M2.3-5 (`A4`), FB-M2.3-7 (`B2`), FB-M2.3-8 (`C1/C2`). The rest are
  regression pins for behavior judged contract-compliant or pending a contract ruling (`D1`).

## 5. Verdict

**M2_3_RECONCILIATION_REQUIRED.** No CRITICAL/HIGH — the deterministic core, the happy-path idempotency,
fold-content stability (R2), hermiticity, and the frozen-module invariant all held under attack. But seven
MEDIUM findings sit on the package's own ratified contracts: the declared decision table is incomplete
(FB-M2.3-2), one consolidation credits two principals (FB-M2.3-1), supersession bookkeeping split-brains and
grows unbounded in `audit=False` mode (FB-M2.3-3), a stable fact self-supersedes its own successors
indefinitely (FB-M2.3-4), rejected promotions re-append events on every rerun (FB-M2.3-5), the freshly
ratified E.4 digest wording is not what the fold ships (FB-M2.3-6, needs the FB-M2.2-3 ruling
re-applied), and malformed provenance both silently disables dedupe and crashes the public seam with a raw
`TypeError` (FB-M2.3-8).

**Most dangerous attack (if any single one):** **FB-M2.3-8's crash + FB-M2.3-5's non-sticky rejection,
combined** — one malformed committed memory (int `evidence_ids`, reachable through the public
`MemoryWriter.remember` with no provenance schema) permanently bricks every future `consolidate()` on that
log with an untyped exception, while any injected-writer rejection silently grows the log by three events
per rerun. Together they turn the two headline promises — hermetic determinism and "re-run appends zero
events" — into single-caller-reachable violations.