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