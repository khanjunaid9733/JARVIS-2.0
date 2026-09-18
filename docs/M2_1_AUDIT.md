# M2.1 Adversarial Verification Audit (Memory API + Episodic Trace)

**Audited Target:** `task/m2.1` @ [`af99696`](file:///F:/JARVIS2.0)  
**Auditor:** Antigravity (Independent Engineering & Quality Reviewer)  
**Date:** 2026-09-19  
**Handoff Source:** [`docs/M2_1_KICKOFF.md`](file:///F:/JARVIS2.0/docs/M2_1_KICKOFF.md)  
**Test Suite Standing:** **`312 passed in 16.31s`** (zero failures, zero regressions across Modules 1–17 + M2.1)

---

## 1. Executive Summary & Verdict

Antigravity has conducted an independent engineering and quality audit of the M2.1 package comprising:
* **Episodic Trace Writer** ([`src/jarvis/kernel/memory_trace.py`](file:///F:/JARVIS2.0/src/jarvis/kernel/memory_trace.py)): Single-event `memory.trace.recorded` writer with `DoneGate` verification and schema confidence clamping.
* **Combined Projection** ([`src/jarvis/kernel/memory_index.py`](file:///F:/JARVIS2.0/src/jarvis/kernel/memory_index.py)): Replay-order pure fold over `memory.write.committed` and `memory.trace.recorded` with NAT-03 canonical digest.
* **Memory API Facade** ([`src/jarvis/kernel/memory_api.py`](file:///F:/JARVIS2.0/src/jarvis/kernel/memory_api.py)): Thin deterministic wrapper delegating lexical recall over the union of memories and traces with total order `(-score, event_id)`.
* **CLI Command** ([`src/jarvis/cli.py`](file:///F:/JARVIS2.0/src/jarvis/cli.py)): Deterministic offline `jarvis recall "<query>"` command.
* **Hermetic Tests** ([`tests/kernel/test_memory_trace.py`](file:///F:/JARVIS2.0/tests/kernel/test_memory_trace.py), [`test_memory_index.py`](file:///F:/JARVIS2.0/tests/kernel/test_memory_index.py), [`test_memory_api.py`](file:///F:/JARVIS2.0/tests/kernel/test_memory_api.py), [`tests/test_cli.py`](file:///F:/JARVIS2.0/tests/test_cli.py)): 20 new tests validating writer, index, api, and CLI.

### Audit Verdict: **`M2.1_RECONCILIATION_READY`**
The architecture adheres to additive-first invariants: no frozen module's existing behavior changed, and all other
frozen modules (1–17) are byte-identical; `src/jarvis/cli.py` gained the creator-ratified `recall` subcommand
(additive, 0 deletions, contract item E). All 312 tests pass cleanly offline; tamper detection and replay
verification halt with `EventIntegrityError` (NAT-04). Note: the M2.1 projection (`MemoryIndex`) provides a
separate digest of its own state shape from module-7's — a creator ruling, see `docs/M2_1_RECONCILIATION.md`. 

Five findings (2 Medium, 3 Low) are documented below for Big Pickle to reconcile.

---

## 2. Verification of Contract Items (A – E)

| Item | Contract Requirement | Audit Status | Verified Reality |
| :--- | :--- | :--- | :--- |
| **A** | **`memory.trace.recorded` Event** | **VERIFIED** | Emitted to stream `"memory"` with `kind: "episodic"`, `content`, `source`, `evidence`, and clamped `confidence`. Causal `cause_event_id = evidence[-1] if evidence else None` verified. |
| **B** | **`MemoryTraceWriter`** | **VERIFIED** | Single-event append; reuses frozen `DoneGate` kind `"memory.write"`; gate failure writes zero events and returns `status="rejected"`. Zero model calls; zero network/ambient reads. |
| **C** | **`Memory` API Facade** | **VERIFIED** | `recall()` delegates to Module-11 lexical retriever over memories+traces union; ranking order `(-score, event_id)` is total and stable; bit-identical to Module 11 when no traces exist. |
| **D** | **`MemoryIndex` Projection** | **VERIFIED** | Pure replay-order fold; module 7 `MemoryProjection` is untouched; NAT-03 canonical digest over `model_dump()` verified deterministic across repeated rebuilds. |
| **E** | **CLI `jarvis recall`** | **VERIFIED** | Deterministic offline CLI command prints top hits formatted as `{event_id}  {score:.2f}  [{source}]  {content}`; prints `"no relevant memory"` on non-matching query. |

---

## 3. Adversarial Findings & Recommendations

### Finding `F-M2.1-1`: `record_episodic()` Drops `mission_id` (Seam Disconnect)
* **Severity:** **MEDIUM**
* **Location:** [`src/jarvis/kernel/memory_trace.py:70-79, 106-117`](file:///F:/JARVIS2.0/src/jarvis/kernel/memory_trace.py#L70)
* **Description:** `MemoryTraceWriter.record_episodic()` does not accept or forward `mission_id`. When episodic traces are written during an agent run inside a mission (spec §84.3 / §80.4), `Event.mission_id` defaults to `None`.
* **Impact:** 
  1. Traces recorded during missions are invisible to mission-filtered stream queries (`log.stream(mission_id=...)`).
  2. In [`src/jarvis/kernel/explain.py`](file:///F:/JARVIS2.0/src/jarvis/kernel/explain.py#L95), `explain_event()` relies on `target.mission_id` to evaluate lifecycle state and transition history. Because `mission_id` is missing on trace events, `jarvis explain <trace_event_id>` will report `"state transitions: none (no mission events for this stream)"`.
  3. Precedent: Identical to `F-M14-1` (CRITICAL) and `F-M15-1` (MEDIUM).
* **Proposed Fix:** Add additive parameter `mission_id: str | None = None` to `record_episodic()` and forward it to `Event(..., mission_id=mission_id)`.

---

### Finding `F-M2.1-2`: Premature `float()` Cast on Confidence Bypasses `DoneGate` Rejection Contract
* **Severity:** **MEDIUM**
* **Location:** [`src/jarvis/kernel/memory_trace.py:80`](file:///F:/JARVIS2.0/src/jarvis/kernel/memory_trace.py#L80)
* **Description:** Line 80 executes:
  ```python
  confidence = min(max(float(confidence), 0.0), 1.0)
  ```
  If a caller passes a non-numeric value (e.g. `confidence="high"`, `confidence="unverified"`, or `confidence=None`), Python raises an unhandled `ValueError` or `TypeError`.
* **Impact:** The documented contract specifies: *"On gate failure no event is written and `TraceWriteResult` carries `status='rejected'`."* The uncaught exception crashes the process instead of returning a typed rejection. Furthermore, `DoneGate.evaluate("memory.write", record)` already contains the predicate `_confidence_valid` that safely verifies numeric type and bounds without raising.
* **Proposed Fix:** Guard the float conversion or pass numeric confidence through safely:
  ```python
  if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
      confidence = min(max(float(confidence), 0.0), 1.0)
  ```
  If `confidence` is non-numeric, leave it as passed so `DoneGate.evaluate()` catches it and returns `TraceWriteResult(status="rejected", reason="trace record rejected: confidence_valid")`.

---

### Finding `F-M2.1-3`: `Memory.get()` Boolean `or` Chain Returns `None` on Empty Dict Payloads
* **Severity:** **LOW**
* **Location:** [`src/jarvis/kernel/memory_api.py:71`](file:///F:/JARVIS2.0/src/jarvis/kernel/memory_api.py#L71)
* **Description:** In `Memory.get(event_id)`:
  ```python
  return self._index.memories.get(event_id) or self._index.traces.get(event_id)
  ```
* **Impact:** In Python, an empty dict `{}` evaluates to `False`. If a committed memory exists with an empty payload `{}`, `self._index.memories.get(event_id)` evaluates to `{}` (falsy) and falls through to `traces.get(event_id)`. If `event_id` is not in traces, `None` is returned, falsely reporting that a committed memory does not exist.
* **Proposed Fix:** Check explicit `None` rather than boolean truthiness:
  ```python
  if self._index is not None:
      hit = self._index.memories.get(event_id)
      return hit if hit is not None else self._index.traces.get(event_id)
  ```

---

### Finding `F-M2.1-4`: `self._projection` Undefined on Instance when Initialized via Index or Log
* **Severity:** **LOW**
* **Location:** [`src/jarvis/kernel/memory_api.py:47-55`](file:///F:/JARVIS2.0/src/jarvis/kernel/memory_api.py#L47)
* **Description:** In `Memory.__init__`, `self._projection` is only bound in the `elif projection is not None:` branch. When constructed with `log` or `index`, `self._projection` is never assigned.
* **Impact:** Inconsistent object shape and potential `AttributeError` on introspection or tooling.
* **Proposed Fix:** Initialize both attributes unconditionally:
  ```python
  self._index: MemoryIndex | None = None
  self._projection: MemoryProjection | None = None
  ```

---

### Finding `F-M2.1-5`: Non-Idiomatic Exception Assertions in Test Suite
* **Severity:** **LOW**
* **Location:** [`tests/kernel/test_memory_index.py:73-77`](file:///F:/JARVIS2.0/tests/kernel/test_memory_index.py#L73), [`tests/kernel/test_memory_api.py:100-105`](file:///F:/JARVIS2.0/tests/kernel/test_memory_api.py#L100)
* **Description:** Tests use manual `try ... raise AssertionError ... except Exception` blocks rather than standard `pytest.raises`.
* **Proposed Fix:** Use standard pytest idioms:
  ```python
  with pytest.raises(EventIntegrityError):
      MemoryIndex.rebuild(log)
  
  with pytest.raises(ValueError, match="Memory requires"):
      Memory()
  ```

---

## 4. Upstream & Working Tree Status

* **Branch:** `task/m2.1` @ commit [`af99696`](file:///F:/JARVIS2.0).
* **Base:** `main` @ [`4af23d4`](file:///F:/JARVIS2.0) (fully synchronized with `origin/main`).
* **Test Suite:** **`312 passed in 16.31s`**.
* **Working Tree:** Clean.
