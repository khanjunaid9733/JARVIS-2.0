# Module 16 — Budget Accounting Ledger (Implementation Note)

Ratifies the M1.1 STRETCH "budget accounting display" intent (spec §134.1,
§80.4). Author: Big Pickle (OpenCode), 2026-09-18. Target: `main` @
`f89ad5f`. No adversarial advisory pass yet — pending handoff.

## 1. What it adds

`jarvis.kernel.budget_ledger` — a pure, ordered fold over the
integrity-verified log:

- `BudgetLedger.rebuild(events)` → frozen `{stream_id: StreamBudget}`.
- `StreamBudget`: `stream_id`, `model_calls`, `deterministic_fallbacks`,
  `attempts`, `spent_tokens`, `allocation_tokens`, `first_asked_event_id`;
  property `questions` and `allocation` ("unbounded" when no declared cap).
- `BudgetLedger.total()` → rollup across streams.
- `stream_budget(stream_id)` → the slab or None.

## 2. Accounting key and inputs

- Every `question.asked` (module 15) folds under `mission_id` when the event
  carries one, else its `stream_id` (per-mission budget, §80.4). `session`
  is the default stream.
- `mission.started` (module 14 intake) contributes an ALLOCATION when the
  payload declares `budget.tokens` or flat `budget_tokens` (a non-negative
  int; anything else is ignored — the ledger refuses to fabricate a cap).
- `model_calls` counts `fallback="model"`; deterministic fallbacks are counted
  separately, so the display is honest about which questions actually consumed
  a model call.

## 3. Determinism and honesty

- Fold order = replay order; no clock, no RNG, no writes. Identical logs →
  identical ledgers (G20/NAT-03 disclosure: cross-run digest not promised
  since timestamps differ).
- `spent_tokens` sums exactly what `question.asked` events carried. The
  module-6 adapter returns only `choices[0].message.content` and never
  surfaces `usage`; adding it would change module-6 behavior, which M1.1
  forbids. So today the sum is 0 and is rendered "0 tokens accounted of
  allocation unbounded". The `tokens` payload key is the forward-compatible
  seam for an adapter that reports usage (M2).

## Suite

Budget behavior covered in `tests/kernel/test_budget_ledger.py`
(empty / model+fallback / non-int token ignore / mission allocation / flat
`budget_tokens` / per-stream grouping / sorted-stable streams) and surfaced
in `tests/kernel/test_explain.py`. 288 passed.

## Post-audit reconciliation (Antigravity pass, 2026-09-18)

| Finding | Severity | Resolution |
| :--- | :--- | :--- |
| F-M16-1 unguarded `int(payload["attempts"] or 0)` crashed the fold on a non-numeric payload — a replay poison pill | MEDIUM | **Fixed** — dedicated `_bounded_count()` (non-negative `int` only, else 0), matching the `spent_tokens` guard. `test_non_numeric_attempts_do_not_break_the_fold` covers a string and a negative value. |