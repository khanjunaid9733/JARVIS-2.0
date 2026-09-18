# Module 14 — Implementation Note (Micro-BP → ratify/refine)

Ratifies the `docs/MODULE14_KICKOFF.md` §2 contract with one documented
refinement. Author: Big Pickle (OpenCode), 2026-09-18. Worktree branch
`task/m1.1-mod14`.

## 1. Intake correction (the one contract change)

The kickoff lists `intent.accepted (module 3)` as an intake event. That event
type does NOT exist in the codebase today: module 3 (`validate_proposal`)
is synchronous and emits no events (it returns `Manifest | ValidationFailure`).

**Refinement:** Module 14 defines its own `mission.started` intake event on
the `mission` stream as the `pending -> executing` trigger. The orchestrator
(or the creator, via a future CLI path) appends `mission.started`; the FSM
consumes it. Nothing else changes in the contract.

`task.completed` / `task.completion_refused` are already tagged with
`mission_id` by `CompletionGate` (module 10) — those flow as-is.
`effect.*` events (module 8) currently carry no `mission_id`; the M2
orchestrator tags them. Module 14's intake filter is `event.mission_id ==
mission_id`, and tests exercise it with tagged events. This is documented,
not silently assumed.

## 2. The DATA transition table (unchanged from kickoff)

```text
pending      + mission.started           -> executing   (emit lifecycle.accepted)
executing    + task.completed            -> completed   (emit lifecycle.completed)
executing    + task.completion_refused   -> refused     (emit lifecycle.refused)
executing    + effect.failed             -> compensated (emit lifecycle.compensated)
```

Judgment call (documented): `effect.refused` (NAT-01 style) folds into the
effect tracking but does NOT terminate the mission — a sub-effect refusal is
not a mission refusal; the orchestrator's later (un)gated completion drives
`refused`. `lifecycle.*` events are never intake — the fold ignores them, so
append -> fold -> append cannot loop.

## 3. Loop-safety

- FSM emits `lifecycle.*` on stream "mission" only, and only when a
  transition fires.
- The fold treats `lifecycle.*` as no-ops (no transition table entries).
- `advance()` only appends a lifecycle event when the corresponding
  `(event_type, cause_event_id)` does not already exist in the log → a second
  `advance()` after a restart appends nothing (idempotent, NAT-05-adjacent).

## 4. Determinism

- `MissionLifecycle.rebuild(mission_id, log)` folds the integrity-verified
  replay slice. Identical logs → identical state and digest.
- Cross-run digest NOT promised (payloads carry wall-clock timestamps) —
  same disclosure as NAT-03/G20.
- Digest = sha256(canonical JSON of state), mirroring `MemoryProjection`.

## 5. F-E15 residual

`MissionLifecycleOwner.build_effect_engine(...)` constructs an
`EffectEnvelopeEngine` with the owner's `observer` always threaded, so any
engine this module builds emits `jarvis.effect.execute` /
`jarvis.verify.postconditions` spans with a caller. No observer → NoOp,
unchanged behavior.

## 6. NAT-05

The owner NEVER appends `task.completed` — it consumes it. That emission
remains exclusively `CompletionGate`'s. Asserted in tests.

## 7. Post-ratification reconciliation (Antigravity adversarial pass, 2026-09-18)

`@ 34496be` was reviewed adversarially (Freebuff limit-hit; Antigravity ran
the pass). Reconciliation `@ f31f87f`:

| Finding | Severity | Resolution |
| :--- | :--- | :--- |
| F-M14-1 engine-built effects invisible to `_slice()` (envelope emits `mission_id=NULL`) | CRITICAL | **Fixed** — additive `mission_id` seam on `EffectEnvelopeEngine` (default None = module-8 behavior unchanged); `build_effect_engine()` binds it. Engine-emitted `effect.*` events now fold into the lifecycle. |
| F-M14-2 `compensated` absorbing dropped later failures in multi-effect missions (§83) | HIGH | **Fixed** — only `completed`/`refused` are fully absorbing; `compensated` keeps folding the effect/compensation ledger so EVERY failed effect is recorded. |
| F-M14-3 `pending` + `task.completed` stranded a zombie state | MEDIUM | **Fixed** — added `pending → completed` / `pending → refused` cells (CompletionGate is authoritative, NAT-05). |
| F-M14-4 `dict(...)` on non-dict `intended_change` could crash fold/replay | MEDIUM | **Fixed** — guarded coercion; non-dict preserved under a `"raw"` key. |
| F-M14-5 `EffectRecord.phase` accepted non-effect event types | LOW | **Fixed** — phase updates restricted to `_EFFECT_EVENT_TYPES`. |
| F-M14-6 concurrent same-mission `advance()` could double-append lifecycle events | LOW | **Accepted + documented** — `advance()` is the orchestrator's synchronous single-writer fold in M1.1; duplicate lifecycle events are no-ops to the fold. |

Contract consequences (disclosed, not silent):

1. **Compensation ledger** — `compensated` is terminal for TRANSITIONS but a
   rolling terminal for the ledger: `compensation`/`effects`/`event_count`
   keep folding. `CompensationRecord.status` stays `"declared"` until M2
   compensators land (§83 seam) — `"pending"`/`"executed"` remain the stated
   M2 progression, not dead code.
2. **Effect visibility** — module 14 no longer relies on the M2 orchestrator
   tagging effect events: the envelope engine stamps `mission_id` when built
   through `build_effect_engine()`. Standalone module-8 engines (no
   `mission_id`) behave exactly as before.

Suite after reconciliation: **267 passed** (243 baseline + 19 module-14 +
5 review-contract tests).