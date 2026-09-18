# M1.1 STRETCH Adversarial Verification Audit (Modules 15, 16, 17)

**Audited Target:** `main` @ [`324e507`](file:///F:/JARVIS2.0)  
**Auditor:** Antigravity (Independent Engineering & Quality Reviewer)  
**Date:** 2026-09-18  
**Handoff Source:** [`docs/M1_1_ADVERSARIAL_HANDOFF.md`](file:///F:/JARVIS2.0/docs/M1_1_ADVERSARIAL_HANDOFF.md)  
**Test Suite Standing:** **`288 passed in 16.63s`** (zero failures, zero regressions)

---

## 1. Executive Summary & Verdict

Antigravity has executed a rigorous, independent adversarial audit of the M1.1 STRETCH completion comprising:
* **Module 15** ([`src/jarvis/kernel/model_answer.py`](file:///F:/JARVIS2.0/src/jarvis/kernel/model_answer.py)): Model-backed structured answering and grounding
* **Module 16** ([`src/jarvis/kernel/budget_ledger.py`](file:///F:/JARVIS2.0/src/jarvis/kernel/budget_ledger.py)): Deterministic per-stream budget accounting ledger
* **Module 17** ([`src/jarvis/kernel/explain.py`](file:///F:/JARVIS2.0/src/jarvis/kernel/explain.py)): Full cause-chain, lifecycle, provenance, and budget explanation renderer
* **CLI Wiring** ([`src/jarvis/cli.py`](file:///F:/JARVIS2.0/src/jarvis/cli.py)): Additive gateway construction, model-grounded `say`, and complete `explain` rendering
* **Seam Extensions** ([`src/jarvis/kernel/model_gateway.py`](file:///F:/JARVIS2.0/src/jarvis/kernel/model_gateway.py), [`src/jarvis/providers/openai_compatible.py`](file:///F:/JARVIS2.0/src/jarvis/providers/openai_compatible.py)): Additive `input_text` forwarding

### Audit Verdict: **`M1.1_RECONCILIATION_READY`**
The core functionality is robust, hermetically tested, and fully grounded against live and simulated backends. Four findings (3 Medium, 1 Low) have been identified for Big Pickle to reconcile before final M1.1 freeze and M2 advance.

---

## 2. Verification of Audit Targets (T1 – T5)

| Target | Description | Audit Status | Verified Evidence |
| :--- | :--- | :--- | :--- |
| **T1** | **Additive `input_text` Seam** | **VERIFIED** | When `input_text=None`, `ModelGateway` forwards no new key, and `OpenAICompatibleAdapter` falls back byte-identically to `"Emit exactly one JSON object."`. All Module 6 baseline unit tests remain green without modification. |
| **T2** | **Module 15 Grounding & Audit** | **VERIFIED** | Question and recalled memory context are properly structured into the prompt. Offline path appends zero events (8 events after init+remember); gateway path appends exactly one `question.asked` event. |
| **T3** | **Module 16 Budget Ledger** | **VERIFIED** | Pure replay-order fold; honest token accounting (0 accounted until adapter surfaces usage); per-mission allocation properly bound to `mission.started`. |
| **T4** | **Module 17 Explain Renderer** | **VERIFIED** | Pure read-only fold; §127.1 assertions (`cause chain: …`, `memory content: '…'`) remain byte-stable. Root-first cause traversal verified live. |
| **T5** | **Hermetic Test Hygiene & Live Resilience** | **VERIFIED** | Tested with invalid API keys and unreachable endpoints in an isolated environment. The system gracefully fell back to deterministic memory extraction, printing `(confidence 1.00, source: session 1)` with full `transport_error` audit provenance. |

---

## 3. Adversarial Findings & Recommendations

### Finding `F-M15-1`: `answer_question()` Drops `mission_id` (Seam Disconnect)
* **Severity:** **MEDIUM**
* **Location:** [`src/jarvis/kernel/model_answer.py:92-101, 209-249`](file:///F:/JARVIS2.0/src/jarvis/kernel/model_answer.py#L92)
* **Description:** `answer_question()` and its internal event logger `_record_question()` do not accept a `mission_id` parameter. When a model answer is executed in the context of an active mission, the emitted `question.asked` event carries `mission_id=None` and `stream_id="session"`.
* **Impact:** In [`src/jarvis/kernel/budget_ledger.py`](file:///F:/JARVIS2.0/src/jarvis/kernel/budget_ledger.py#L93), budget is keyed by `event.mission_id or event.stream_id`. Because `mission_id` is dropped, model call attempts and tokens spent during a mission are attributed to the global `"session"` slab instead of the mission's allocation slab (§80.4).
* **Proposed Fix:** Add additive keyword parameter `mission_id: str | None = None` to `answer_question()` and `_record_question()`, and pass `mission_id=mission_id` when constructing `Event(stream_id=SESSION_STREAM_ID, ...)`.

---

### Finding `F-M16-1`: Unguarded `int()` Coercion on `attempts` (Replay Poison Pill)
* **Severity:** **MEDIUM**
* **Location:** [`src/jarvis/kernel/budget_ledger.py:100`](file:///F:/JARVIS2.0/src/jarvis/kernel/budget_ledger.py#L100)
* **Description:** Line 100 executes:
  ```python
  slab["attempts"] += int(event.payload.get("attempts") or 0)
  ```
  While `spent_tokens` at line 102 is safely guarded with `isinstance(tokens, int) and tokens >= 0`, `attempts` performs an unchecked `int()` cast.
* **Impact:** If an event log row contains a malformed or string payload (e.g. `{"attempts": "many"}`), `BudgetLedger.rebuild()` crashes with an unhandled `ValueError`, poisoning replay and breaking the pure fold invariant (G20 / NAT-03).
* **Proposed Fix:** Use defensive type-checking mirroring the `tokens` pattern:
  ```python
  raw_attempts = event.payload.get("attempts")
  if isinstance(raw_attempts, int) and raw_attempts >= 0:
      slab["attempts"] += raw_attempts
  ```

---

### Finding `F-M17-1`: Unbounded Cause-Chain Traversal (Infinite Loop on Cycles)
* **Severity:** **MEDIUM**
* **Location:** [`src/jarvis/kernel/explain.py:85-87`](file:///F:/JARVIS2.0/src/jarvis/kernel/explain.py#L85)
* **Description:** The cause-chain walk follows parent pointers using an unbounded `while` loop:
  ```python
  while current is not None:
      root_chain.append(current)
      current = by_id.get(current.cause_event_id) if current.cause_event_id else None
  ```
* **Impact:** If an event has a self-referential `cause_event_id == event_id` or corrupt/tampered event logs contain a cyclic dependency, `explain_event()` loops infinitely, freezing the process.
* **Proposed Fix:** Add a cycle detector:
  ```python
  seen: set[str] = set()
  while current is not None and current.event_id not in seen:
      if current.event_id:
          seen.add(current.event_id)
      root_chain.append(current)
      current = by_id.get(current.cause_event_id) if current.cause_event_id else None
  ```

---

### Finding `F-M17-2`: Tuple Literal Default for Declared `list` Fields
* **Severity:** **LOW**
* **Location:** [`src/jarvis/kernel/explain.py:58, 60`](file:///F:/JARVIS2.0/src/jarvis/kernel/explain.py#L58)
* **Description:** In `Explanation(BaseModel)`:
  ```python
  lifecycle_transitions: list[str] = ()
  recalled_memories: list[RecalledMemory] = ()
  ```
  Because Pydantic does not enforce default validation without explicit configuration, default instances hold Python `tuple` objects (`<class 'tuple'>`) rather than `list`.
* **Impact:** Callers expecting a standard `list` (e.g. attempting `.append()`) will encounter runtime `AttributeError`.
* **Proposed Fix:** Use Pydantic's standard field defaults:
  ```python
  lifecycle_transitions: list[str] = Field(default_factory=list)
  recalled_memories: list[RecalledMemory] = Field(default_factory=list)
  ```

---

## 4. Upstream Synchronization Status

* **Push Status:** **Fully Synchronized.**
* **Remote HEAD:** `origin/main` is at commit [`324e507`](file:///F:/JARVIS2.0), verified on GitHub while public.
* **Working Tree:** Clean, 0 uncommitted changes.
