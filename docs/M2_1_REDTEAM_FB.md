# Freebuff — Adversarial Review Report (M2.1)
## Milestone 2 · Package M2.1 — Memory API + Episodic Trace

**Reviewer:** Freebuff / DeepSeek (adversarial architecture & research reviewer)
**Target:** branch `task/m2.1` @ **`af99696`** (`feat(kernel): M2.1 memory API + episodic trace (contract A-E ratified)`)
**Date:** 2026-09-19
**Status of findings:** **PROPOSALS** — not accepted architecture. No `src/` file was modified.
**Baseline:** 312 passed (pre-existing suite) · **with evidence probes: 328 passed**
**Verdict:** **NO CRITICAL findings.** 9 findings (0 CRITICAL / 4 MEDIUM / 5 LOW). The additive-first
invariant, the NAT-04 delegation, the gate-before-append ordering, and the offline CLI all held.

---

## 1. Preconditions (reproduced, not quoted)

| Check | Observed |
| :--- | :--- |
| Branch / HEAD | `task/m2.1` @ `af996964a78b66c1935e765cc362d635dbf46746` |
| Working tree at review time | clean except untracked `docs/M2_1_AUDIT.md`, `docs/M2_1_REDTEAM_PROMPT_FB.md` |
| Baseline suite | `312 passed in 13.37s` — matches the prompt; no mismatch to report |
| Interpreter | 3.12.x (conftest gate satisfied; no banner finding) |
| Lock drift | none (`uv.lock` clean after every run) |
| Additive-first | `git diff 86a1369 af99696` = **626 insertions, 0 deletions** across 8 files |

**Pristine re-verification worktree:** `F:\JARVIS-fb-m2-1` (detached at `af99696`) — created because a
concurrent reconciliation session began editing `src/` in the shared checkout mid-review (§4).
Evidence run there: `16 passed` (probes) and `328 passed` (full suite).

---

## 2. Findings

### F-M2.1-FB-1 — MEDIUM — recall cannot distinguish a verified memory from an unverified trace
**Location:** `src/jarvis/kernel/memory_query.py:42-48` (`RecalledMemory{event_id, content, source, score}`)
consumed at `src/jarvis/kernel/memory_api.py:66-67`; rendered at `src/jarvis/cli.py:285`.
**Failure mode:** §84.3 defines two tiers precisely because they differ in verification: `memory.write.committed`
passed the deterministic gate; `memory.trace.recorded` is a caller-declared raw record that passed only the same
cheap gate (and, currently, can bypass it — see §4). `Memory.recall()` merges both into one ranked list of
identically-shaped records with **no tier/verification field**, so no consumer — including `jarvis recall` — can tell
an established memory from a raw observation. A trace asserting `the safe word is umbrella` from `agent.guess`
is returned with the same shape and the same score as a committed memory asserting the same thing.
**Evidence:** `test_c1_recall_cannot_distinguish_verified_memory_from_raw_trace` (PASSES at `af99696`):
two hits, `score == score`, `set(hit.model_dump()) == {"event_id","content","source","score"}`.
**Recommendation:** carry the discriminator through retrieval (additive `kind`/`tier` on `RecalledMemory`, populated
from which fold map the hit came from) and print it in `_cmd_recall`. Smallest change that stops the conflation;
M2.3 consolidation needs this field to know which tier it is reading.

### F-M2.1-FB-2 — MEDIUM — one log, two incomparable "NAT-03 canonical state" digests
**Location:** `src/jarvis/kernel/memory_index.py:70-72` vs `src/jarvis/kernel/memory_projection.py` `digest()`;
selected by constructor path at `src/jarvis/kernel/memory_api.py:74-76`.
**Failure mode:** `project_state.yaml:97` defines the NAT-03 digest as `last_seq, event_count, streams, providers,
memories` (module 7). `MemoryIndex.digest()` hashes a **different state shape** — no `providers`, plus `traces` — yet
`M2_1_KICKOFF.md §3 D` calls it "digest() over canonical state (NAT-03)". `Memory(log=...).digest()` returns the new
one; `Memory(projection=...).digest()` returns the old one. The two are not comparable, so a restart/recover
comparison that uses the wrong construction path reports spurious divergence for an identical log — or, worse,
agrees while hiding provider-state divergence, because the M2.1 digest is **blind to provider identity**: two logs
differing only in which provider was registered produce the *same* `MemoryIndex.digest()` (the `streams` map only
records per-stream sequence numbers) and *different* module-7 digests.
**Evidence:** `test_b1_same_log_yields_two_different_nat03_digests` and
`test_b2_memoryindex_digest_is_blind_to_provider_identity` (both PASS at `af99696`).
**Recommendation:** pick one canonical definition before M2.10 (checkpoint/recovery) consumes it. Either fold providers
into `MemoryIndex` and declare it the single NAT-03 digest, or rename the M2.1 one to a scoped
`memory_state_digest()` so it cannot be mistaken for the full projection digest. This is a creator decision, not a
code fix.

### F-M2.1-FB-3 — MEDIUM — a bare-string `evidence` is silently char-split into fake event ids
**Location:** `src/jarvis/kernel/memory_trace.py:81` (`evidence = [str(ref) for ref in (evidence or [])]`), consumed
at `:107` (`cause_event_id=evidence[-1]`).
**Failure mode:** the declared type is `list[str] | tuple[str, ...] | None`, but a bare `str` is itself iterable and is
accepted without complaint. `record_episodic(..., evidence="01ARZ3NDEKTSV4RRFFQ69G5FAV")` stores 26 single-character
"references" and sets `cause_event_id="V"` — a causal link pointing at an event that never existed. §112 requires
causal links point backward at real events; a trace that *looks* causally grounded here is not. It is silent: the
`TraceWriteResult` reports `status="recorded"`.
**Evidence:** `test_a1_evidence_as_bare_string_is_silently_char_split` (PASSES at `af99696`;
`trace.cause_event_id == "V"`, marked `# FLIPS ON FIX`).
**Recommendation:** treat `str`/`bytes` as a single element (`if isinstance(evidence, str): evidence = [evidence]`) or
raise a typed error. One line.

### F-M2.1-FB-4 — MEDIUM — contract item B is not implemented: `TraceWriteResult` has no `correlation_id`
**Location:** `src/jarvis/kernel/memory_trace.py:43-49`.
**Failure mode:** `M2_1_KICKOFF.md §3 B` ratifies `TraceWriteResult{status: "recorded", event_id, correlation_id}`.
The shipped model is `{status, reason, event_id, gate}` — the ratified `correlation_id` is absent. The event itself
does carry a correlation id (`:108`), but a caller cannot obtain it from the returned result without re-reading the
log, which is exactly what the ratified contract exists to avoid (multi-step mission/saga chaining, §3 A).
**Evidence:** `test_a3_trace_result_does_not_expose_correlation_id` (PASSES at `af99696`; asserts the field set).
**Recommendation:** add `correlation_id: str | None = None` to `TraceWriteResult` and populate it on the recorded
branch (it equals `event_id` unless the caller supplied one). Purely additive.

### F-M2.1-FB-5 — LOW — non-iterable `evidence` escapes the typed-result contract
**Location:** `src/jarvis/kernel/memory_trace.py:81`.
**Failure mode:** `evidence=12345` raises `TypeError: 'int' object is not iterable` out of `record_episodic`, so the
documented outcome channel (`TraceWriteResult`) never materialises, and no rejection is reported. Same class as
Antigravity `F-M2.1-2`, different input (`evidence` rather than `confidence`).
**Evidence:** `test_a2_non_iterable_evidence_escapes_the_typed_result` (PASSES at `af99696`; `pytest.raises(TypeError)`
and `log.replay() == []`).
**Recommendation:** fold into the F-M2.1-FB-3 guard — coerce to a list, or reject through `DoneGate`/typed result.

### F-M2.1-FB-6 — LOW — a refused trace leaves no trace in the log
**Location:** `src/jarvis/kernel/memory_trace.py:88-99` (gate runs before `EventLog.append`; the rejected branch returns
without appending).
**Failure mode:** this is **contract-compliant** (`§3 B`: "On gate failure no event is written"), but it is asymmetric
with module 10, whose writer appends `memory.write.rejected` for the same gate kind
(`src/jarvis/kernel/memory_write.py`). A refused trace is therefore invisible to replay and to any audit that works
off the log — the same unattributability class the M1 review raised as F-A2 for refused effects.
**Evidence:** `test_a4_rejected_trace_leaves_no_audit_event` (PASSES at `af99696`; `log.replay() == []`).
**Recommendation:** creator ruling, not a code fix: either accept the asymmetry (documented) or emit a
`memory.trace.rejected` audit event that is excluded from `MemoryIndex.traces`. Do not change `MemoryIndex` folding
without the ruling, since `traces` is a digest input.

### F-M2.1-FB-7 — LOW — the audit's "Modules 1–17 remain byte-identical" claim is false for `cli.py`
**Location:** `docs/M2_1_AUDIT.md` §1 (and `docs/M2_1_KICKOFF.md §2`, "M2.1 must NOT change modules 1–17");
ground truth `git diff --name-status 86a1369 af99696` → `M src/jarvis/cli.py`, `M tests/test_cli.py`.
**Failure mode:** the change is **purely additive (0 deletions)** and explicitly authorized by ratified contract item E,
so the *behavior* of module 11 is untouched — but the audit sentence is the artifact downstream readers will cite as
evidence of the additive invariant, and taken literally it is inaccurate. A later reviewer cannot distinguish
"sanctioned additive CLI surface" from "frozen module was edited" using that sentence.
**Evidence:** `git diff --stat 86a1369 af99696` → 626 insertions, 0 deletions; `cli.py` +20 lines.
**Recommendation:** reword to "no frozen module's existing behavior changed; `cli.py` gained the ratified `recall`
subcommand (additive, 0 deletions)". Documentation only.

### F-M2.1-FB-8 — LOW — `limit` is unvalidated; a negative limit silently truncates
**Location:** `src/jarvis/kernel/memory_api.py:66-67` → `memory_query.recall` `scored[:limit]`.
**Failure mode:** `limit=-1` returns all-but-the-last hit instead of raising or returning nothing. Deterministic but
wrong-looking to a caller, and `Memory` is the facade other packages will call.
**Evidence:** `test_c4_negative_limit_silently_truncates` (PASSES at `af99696`; 2 hits → `limit=3` gives 2,
`limit=-1` gives 1).
**Recommendation:** `if limit < 0: raise ValueError(...)`. One line.

### F-M2.1-FB-9 — LOW/NIT — multiline content breaks the CLI hit-per-line format
**Location:** `src/jarvis/cli.py:285` (`print(f"{hit.event_id}  {hit.score:.2f}  [{hit.source}]  {hit.content}")`).
**Failure mode:** a trace whose content contains newlines (plausible for a raw episodic record) emits several output
lines for one hit, so the documented one-line-per-hit contract no longer holds for any consumer parsing stdout.
**Evidence:** `test_d1_cli_recall_multiline_content_breaks_hit_per_line` (PASSES at `af99696`).
**Recommendation:** escape/shorten the content (e.g. `content.replace("\n", " ")` or `repr`).

---

## 3. No-findings surfaces (attacked, nothing broke)

| Surface | Result |
| :--- | :--- |
| Event-id collision between `memories` and `traces` | **Impossible** — `events.event_id` is `UNIQUE` in the schema and one event has one `event_type`; the two maps are keyed by that same unique id with disjoint predicates (`memory_index.py:59-61`). |
| Out-of-order / regressing `stream_seq` | **Not reachable** — `stream_seq` is `NOT NULL`, assigned `MAX(stream_seq)+1` per stream (`event_log.py:186`), and `replay()` orders by global `seq`; the `or 0` at `memory_index.py:57` can never fire on replayed rows. |
| Digests across dict ordering / object serialization | **Deterministic** — `_canonical_json` uses `sort_keys=True`; `rebuild` twice → identical state *and* digest (`test_rebuild_is_deterministic_digest_stable` plus my B1 run). |
| NAT-04 tamper halt through the new projection | **Holds** — `MemoryIndex.rebuild` delegates to `EventLog.replay()`, which verifies payload hash → chain hash → event hash per row before returning (`event_log.py:341-359`). |
| Gate-before-emit ordering (rejection emits nothing) | **Holds** — `decision = self._gate.evaluate(...)` precedes `EventLog.append` on the only emitting branch (`memory_trace.py:88-99`). |
| Trace-writer determinism | **No clock, no RNG, no network, no ambient reads** in the writer; repeated calls append distinct events by design (episodic = occurrence). |
| `Memory(log).recall() == Memory(projection).recall()` with no traces | **Confirmed** — matches contract item C's "bit-identical to module 11 when no traces exist". |
| CLI offline hermeticity | **Confirmed** — `recall` returns 0 with `JARVIS_MODEL_BASE_URL=http://127.0.0.1:9/v1` and a bogus key, i.e. it never dials out (`test_d2`), and an empty query is handled without inventing a match (`test_d3`). |
| Scope boundary (no embeddings/consolidation/PII/fs/authority/budgets/checkpoints) | **No leakage found** in the M2.1 diff; module 7 `MemoryProjection` and all other frozen modules are untouched by `af99696`. |
| NaN `confidence` reaching `payload_json` | **Not reachable** via the trace writer — NaN survives `min(max(...))` but `DoneGate._confidence_valid` rejects it, so no non-canonical (`NaN`) payload is stored (`test_a7`). |
| `Memory()` with no input | **Raises `ValueError`** as documented (`test_constructor_requires_an_input`). |

---

## 4. Closed-in-flight (found at `af99696`, fixed by the concurrent reconciliation)

While this review ran, a reconciliation session began editing the shared checkout. At `af99696` I confirmed two
findings that the in-flight edits already close; they are recorded here as **regression pins**, not as open work.

> **Was MEDIUM — pre-gate `float()` coercion launders values the same gate kind rejects.**
> `memory_trace.py:80` (`confidence = min(max(float(confidence), 0.0), 1.0)`) ran *before* the gate, so
> `confidence=True` became `1.0` and `confidence="0.5"` became `0.5` — and the identical `"memory.write"` gate that
> **rejects** both for module 10 (`memory_write.MemoryWriter.remember`) then **accepted** them for the trace tier.
> Two tiers, one gate kind, opposite verdicts.
> **Evidence:** `test_a5_trace_gate_launders_bool_confidence_the_same_gate_rejects`,
> `test_a6_trace_gate_launders_numeric_string_confidence` — **PASS at `af99696`**, and **FAIL on the current working
> tree** because the reconciliation's `F-M2.1-2` guard (`isinstance(confidence, (int, float)) and not
> isinstance(confidence, bool)`) landed, making both rejections consistent. Same root cause as Antigravity
> `F-M2.1-2`; that finding's *crash* face and this *silent-acceptance* face are the same defect, so one fix closes both.
> **Review note on the fix:** widening the annotation to `confidence: float | str` advertises a type that is only ever
> rejected; `float | object` or a documented "non-numeric is rejected by the gate" comment would read truer.

Also confirmed closed in the working tree: `F-M2.1-1` (`mission_id` now forwarded) and `F-M2.1-4`
(`Memory.__init__` initialises both attributes). **Still open in the working tree:** every finding in §2.

---

## 5. Spec / ADR conflicts

1. **NAT-03 is now two decisions.** `project_state.yaml:97` (digest = `last_seq, event_count, streams, providers,
   memories`, module 7) vs `M2_1_KICKOFF.md §3 D` + `memory_index.py:70-72` (a second state shape also labelled
   NAT-03). The ledger's `nat_03.status: implemented` note names only module 7, so the ledger no longer describes the
   full surface. → F-M2.1-FB-2.
2. **Contract item B not met.** `M2_1_KICKOFF.md §3 B`
   ("`TraceWriteResult{status: "recorded", event_id, correlation_id}`") vs `memory_trace.py:43-49`. → F-M2.1-FB-4.
3. **§84.3 / §84.4 tiers collapsed at the API boundary.** The two-tier design exists to separate verified from raw
   records; `Memory.recall()` returns them indistinguishably. → F-M2.1-FB-1.
4. **Additive-invariant claim overstated.** `docs/M2_1_AUDIT.md` "Modules 1–17 remain byte-identical" vs
   `M src/jarvis/cli.py` (additive, ratified by item E). → F-M2.1-FB-7.
5. **Scope boundary respected.** No M2.2–M2.10 package was built; the only new event type is `memory.trace.recorded`,
   as specified.

---

## 6. Test proposals (delivered as evidence in this worktree)

| Path | Contents | Outcome |
| :--- | :--- | :--- |
| `tests/review/test_freebuff_redteam_m2_1.py` | 16 probes: A (trace writer), B (projection/digest), C (facade), D (CLI) | **16 passed at `af99696`** (`F:\JARVIS-fb-m2-1`) |
| `tests/review/__init__.py` | package marker | — |
| Full suite @ `af99696` + probes | `uv run --with pytest --with opentelemetry-sdk --with opentelemetry-api --with anyio pytest -q` | **328 passed in 23.70s** |
| Full suite on the live working tree (mid-reconciliation) | same command | **326 passed, 2 failed** — the 2 are A5/A6, which fail *because* the `F-M2.1-2` guard landed |

Probes are written as **behavior pins**: each PASSES on the current behavior and names the assertion that
`# FLIPS ON FIX`, so they become regression tests for items in §2 as their fixes land. Nothing was committed and no
`src/` file was modified; `uv.lock` showed no drift after any run.

---

## 7. Recommended reconciliation order

1. **Before merge:** F-M2.1-FB-1 (add `kind`/`tier` to `RecalledMemory`) and F-M2.1-FB-2 (one canonical digest) —
   both change the contract surface M2.2/M2.10 build on, so they get expensive after merge.
2. **Same-file, small:** F-M2.1-FB-3, F-M2.1-FB-4, F-M2.1-FB-5 (all in `memory_trace.py`), F-M2.1-FB-8 (`memory_api.py`).
3. **Rulings, not code:** F-M2.1-FB-6 (refusal auditability) and F-M2.1-FB-2's digest ownership.
4. **Docs/NIT:** F-M2.1-FB-7 (audit wording), F-M2.1-FB-9 (CLI escaping).
