# M2.1 — Memory API + Episodic Trace Store (Kickoff & Design Contract)

**Status:** PROPOSAL — contract to ratify before any `src/` change.
**Author/owner:** Big Pickle (OpenCode) implements; Freebuff attacks; Antigravity verifies.
**Milestone:** M2 (Memory OS), package M2.1 (of `docs/M2_KICKOFF.md`).
**Baseline:** `main @ 4af23d4`, 292 passed, modules 1–17 FROZEN + creator-signed
(`docs/M1_1_SIGNOFF.md`).
**Proof target (M2):** `read file → evidence → memory trace → restart → recover`.

## 1. Why this exists

Spec §M2 (4957-4980) starts M2 with **episodic traces** and a **memory API**;
§84.3 (two-tier consolidation) begins at the EPISODIC TRACE tier — the raw
record of what happened — which feeds the "cheap search/index" and later the
consolidation pipeline (M2.3). M1 already proves `memory.write.*`
(proposed→verified→committed, gated). M2.1 adds the **trace** tier and a
thin, deterministic **memory API** without building embeddings,
consolidation, PII, or filesystem effects (their packages).

## 2. Grounding in the frozen modules (re-derived, not assumed)

- **module 7** `memory_projection.MemoryProjection` folds
  `memory.write.committed` → `memories: dict[event_id, payload]`, with a
  NAT-03 canonical-state digest. Payloads are the raw committed records.
- **module 10** `memory_write.MemoryWriter.remember(...)` emits
  `memory.write.proposed/verified/committed|rejected` on stream `"memory"`,
  gated by `DoneGate`; payload carries `content/source/confidence/
  memory_class/provenance`. Memory classes today: episodic/semantic/
  procedural.
- **module 11** `memory_query.recall()` = deterministic lexical overlap
  retriever; total order `(-score, event_id)`; `ANSWER_MIN_CONFIDENCE` gate
  on `answer()`. `RecalledMemory{event_id, content, source, score}`.
- **module 15** `model_answer` grounds the gateway path through `recall()`.
- All folds rebuild from `EventLog.replay()` (integrity verified, NAT-04).

Consequence: M2.1 must NOT change modules 1–17. It adds new, standalone
kernel code behind the existing seams (same pattern as modules 14–17).

## 3. Design contract (to be ratified)

```text
A) Episodic trace event
   event_type  : "memory.trace.recorded"           (new; stream "memory")
   payload     : {
       kind        : Literal["episodic"]           // M2.1 records the
                                                    // episodic tier only
       content     : str,                           // the raw trace text
       source      : str,                           // provenance (who/what)
       evidence    : list[str],                     // event_ids / artifact refs
                                                    // linked as causes (may be empty)
       confidence  : float = 1.0,                   // caller-declared initial
                                                    // confidence (schema-clamped
                                                    // to [0,1]) — NOT verification
   }
   causal/correlation discipline: cause_event_id = evidence[-1] when present,
   else None; correlation_id = the trace event's own auto-generated id (or a
   caller-supplied correlation). Same rules as memory.write.* (module 10).

B) Trace writer (single-writer, deterministic, NO model calls / NO effects)
   new module: src/jarvis/kernel/memory_trace.py
   class MemoryTraceWriter:
       record_episodic(*, content, source, evidence=None, confidence=1.0,
                       principal_id=CREATOR_PRINCIPAL_ID) -> TraceWriteResult
   TraceWriteResult{status: "recorded", event_id, correlation_id}
   Like module 10, the writer performs NO principal authority check (F-C9
   disclosure applies); key-based authority is M2.8. The cheap deterministic
   gate (DoneGate) MAY be applied to the trace tier, decided at ratification
   — default: APPLIED (cost is negligible and §84.4 wants verification
   proportional to impact from the start).

C) Memory API (thin deterministic facade — the "memory API" of §M2)
   new module: src/jarvis/kernel/memory_api.py
   class Memory:
       __init__(log, projection_builder=None)      // fold inputs; no runtime
       recall(query, *, limit=3) -> list[RecalledMemory]
            // module-11 recall() semantics over a combined projection that
            // includes BOTH committed semantic memories AND episodic traces
            // (ranking = (-score, event_id) total order; embedding/rerank
            // ranking seam is M2.2, not here)
       get(event_id) -> dict | None                 // raw folded payload
       digest() -> str                              // NAT-03 canonical state digest
   Retrieval ordering stays deterministic and clock-independent.

D) New projection (additive; module 7 untouched)
   new module: src/jarvis/kernel/memory_index.py
   MemoryIndex.rebuild(log): folds memory.write.committed (existing) AND
   memory.trace.recorded into: memories{event_id: payload} and
   traces{event_id: payload}; digest() over canonical state (NAT-03).
   Memory.recall() uses MemoryIndex when available, else falls back to the
   module-7 MemoryProjection (so existing behavior is bit-identical when no
   traces exist).

E) CLI (minimal, optional, ratified)
   - `jarvis recall "<query>"` — print top hits (id, score, source, content)
     from the combined index; deterministic offline.
   - `jarvis say "remember: ..."` stays on the EXISTING module-10 writer
     (unchanged). No new persistence path, no new event types beyond B/D.

Determinism target (mirror NAT-03/G20):
   replay(log) twice -> identical MemoryIndex state + digest. Cross-run
   digest NOT promised (payloads/timestamps carry wall-clock values).

Scope boundaries (do NOT build):
   - no embeddings/reranking/vector index (M2.2)
   - no consolidation/extraction/contradiction (M2.3)
   - no memory verification ladder beyond the existing DoneGate rung (M2.4)
   - no PII detection/redaction (M2.5)
   - no filesystem adapter, no sandbox, no effects execution (M2.6)
   - no key-based authority/signatures (M2.8)
   - no budget/rate-limit enforcement (M2.9)
   - no semantic checkpoints / snapshot recovery (M2.10)
```

## 4. Entry conditions (gates)

1. M1 + M1.1 signed off — **DONE** (`docs/M1_1_SIGNOFF.md`).
2. Modules 1–17 frozen; additive-only behind ratified design — **in force**.
3. `main` in sync with `origin/main` — **DONE** (`4af23d4`).
4. This contract ratified by the creator (accept or refine items A–E),

## 5. Sequencing

1. Ratify items A–E (creator) — including the trace-tier DoneGate question
2. Implement `memory_trace.py`, `memory_index.py`, `memory_api.py` + tests
   (Big Pickle) on a task branch
3. Adversarial pass (Freebuff) on trace/API/projection contracts
4. Independent verify (Antigravity)
5. Merge to `main` only when green; record in `project_state.yaml`

---

## Paste-ready kickoff prompt (implementer)

```markdown
# M2.1 — Memory API + episodic trace store — kickoff

You are Big Pickle (OpenCode), primary implementation engineer.
Baseline: `main @ HEAD`, 292 passed; modules 1-17 FROZEN + creator-signed.

READ FIRST (re-derive from disk, trust nothing quoted):
- docs/M2_KICKOFF.md (M2 scope, proof, package list)
- docs/M2_1_KICKOFF.md §3 (the ratified contract items A-E)
- docs/MASTER_BUILD_SPEC.md §84.3/§84.4, §131.14, §85.2, §127.1
- src/jarvis/kernel/memory_projection.py (fold precedent, NAT-03 digest)
- src/jarvis/kernel/memory_write.py (event types, causal/correlation rules)
- src/jarvis/kernel/memory_query.py (recall ordering, RecalledMemory)
- project_state.yaml (m2_memory_os, truth protocol)

DELIVER:
1. Re-verify the ratified contract against the frozen code first. If you must
   change A-E, say what/why in the implementation note.
2. Implement src/jarvis/kernel/memory_trace.py, memory_index.py,
   memory_api.py + tests/kernel/test_memory_trace.py, test_memory_index.py,
   test_memory_api.py. Task branch task/m2.1; merge only when green.
3. Determinism tests: replay twice -> identical index + digest; identical logs
   -> identical recall ordering. Document cross-run digest not promised.
4. No hidden now()/RNG/network. No new dependencies. No changes to modules 1-17.
5. Optional CLI `jarvis recall` ONLY behind the ratified item E; otherwise none.

Do not build: embeddings, consolidation, PII, filesystem effects, authority,
budgets, checkpoints (their packages). No history rewrites. No push.
```