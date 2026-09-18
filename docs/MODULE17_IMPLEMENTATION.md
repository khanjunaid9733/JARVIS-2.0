# Module 17 — Full `explain` Cause-Chain Rendering (Implementation Note)

Ratifies the M1.1 STRETCH "full explain cause-chain rendering" intent
(spec §134.1). Author: Big Pickle (OpenCode), 2026-09-18. Target: `main` @
`f89ad5f` (kernel) + `b45add7` (CLI). No adversarial advisory pass yet —
pending handoff.

## 1. What it adds

`jarvis.kernel.explain` — a pure, read-only renderer over the
integrity-verified log:

- `explain_event(log, projection, event_id) -> Explanation | None`
  (None when the event is unknown).
- `Explanation`: `target_event_id`, `event_type`, `principal_id`,
  `stream_id`, `chain` (root-first `ChainLink` list walking `cause_event_id`),
  `lifecycle_state` + `lifecycle_transitions`, `model_provenance`,
  `recalled_memories`, `memory_content` + `memory_source`,
  `capability_check_count`, `effect_count`, `budget`.

## 2. Rendering semantics

- **Cause chain**: `cause_event_id` edges walked to the root, displayed
  root-first (`… <- … <- target`); the §127.1 `cause chain:` line is stable.
- **Lifecycle**: when the target carries a `mission_id`,
  `MissionLifecycleOwner.rebuild` (module 14) supplies the state; the
  transition names are the `lifecycle.*` events on that mission slice
  (`LIFECYCLE_EVENT_BY_STATE` domain). No mission → "no mission events for
  this stream".
- **Model provenance**: for `question.asked` targets the payload is echoed
  (provider/contract/model name/answer path) and `recall` re-runs the
  question to list retrieved memories with scores.
- **Memory**: for `memory.write.committed` targets, content + source.
- **Capability / effect confinement**: `policy.check` events and distinct
  `effect.*` `effect_id`s counted over the target's mission slice, else over
  its own cause chain (none on the offline path).
- **Budget**: `BudgetLedger.rebuild(events).stream_budget(mission_id |
  stream_id | "session")` (module 16).

## 3. Determinism

The renderer writes nothing and never calls a model — it is a deterministic
function of the log (G20/NAT-03). The CLI formats the structure; the module
owns the semantics. §127.1 assertions (`cause chain: …`, `memory content:
'…'`) remain intact by construction.

## Suite

Semantics in `tests/kernel/test_explain.py` (unknown target, memory chain,
question-asked provenance, mission lifecycle + transitions, effect/policy
counts, budget slab); CLI view in `tests/test_cli.py`
(`test_explain_renders_full_blocks_for_memory_event`,
`test_model_backed_say_records_question_and_explain_shows_provenance`).
Verified live end-to-end against a real Groq-backed log (see module-15
note §3). 292 passed (288 + reconcile tests).

## 5. Post-audit reconciliation (Antigravity pass, 2026-09-18)

| Finding | Severity | Resolution |
| :--- | :--- | :--- |
| F-M17-1 unbounded `while current is not None:` cause-chain walk loops forever on cyclic / self-referential `cause_event_id` (corrupt log) | MEDIUM | **Fixed** — `seen` set terminates the walk on the repeated node. `test_self_referential_and_cyclic_cause_chains_terminate` covers 1- and 2-node cycles. |
| F-M17-2 tuple literal `()` defaults for list fields (`lifecycle_transitions`, `recalled_memories`) | LOW | **Fixed** — `Field(default_factory=list)`; fresh per-instance lists. `test_explanation_defaults_are_fresh_lists`. |

## Suite

292 passed (288 + reconcile tests).