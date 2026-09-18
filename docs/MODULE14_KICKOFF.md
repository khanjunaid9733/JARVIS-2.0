# Module 14 — Deterministic Mission-Lifecycle FSM (STRETCH M1.1)

**Status:** PROPOSAL — entry conditions drafted; not started.
**Author/owner:** Big Pickle (OpenCode) implements; Freebuff attacks; Antigravity verifies.
**Precedent seam:** standalone, additive, deterministic — same pattern as module 9
(`policy.py`) and module 10 (`done_gate.py`): a stage that is a pure function of
the event stream and its inputs, with no hidden clock/RNG/network.

## 1. Why this exists

Spec §134.1 marks the *full mission-lifecycle FSM* as STRETCH (M1.1). M1 delivered
the deterministic **done gate** (`done_gate.py`) — refrigerant of
`task.completed`, and **effect envelope** (`effect_envelope.py`) — single-effect
`PREPARE → AUTHORIZE → COMMIT → VERIFY`, with multi-effect mission compensation
explicitly deferred. Module 14 closes that gap: the lifecycle schema an M2/M3
orchestrator needs while keeping the kernel deterministic.

`project_state.yaml` records the boundary this module must respect:

- **F-E15 residual:** the CLI constructs no `EffectEnvelopeEngine` today. Module 14
  is the first production consumer — it MUST pass `service.observer` into every
  `EffectEnvelopeEngine` it builds so effect/verify spans finally have a caller.
- **NAT-05:** `CompletionGate` remains the *only* path that emits `task.completed`.
  Module 14 must consume it, never duplicate it.
- **NAT-01/NAT-02:** lifecycle events must carry the same causal/correlation
  discipline (`cause_event_id`, `correlation_id`) already enforced elsewhere.

## 2. Design contract (to be ratified before implementation)

```text
MissionLifecycle (new file src/jarvis/kernel/mission_lifecycle.py)

States (lifecycle.* event types, stream "mission"):
  pending -> executing -> completed | refused | compensated
  Intended_change with FAILED effect -> compensation sub-flow (deferred wire).

Transitions are a DATA table (state, event) -> next state (policy.py precedent:
threshold tables are DATA). The machine evaluates PURELY on appended events:
  step(lifecycle, event) -> (next_lifecycle, events_to_append or [])
No hidden now(): timestamps come from injected event payloads / log clock only.

Integration:
  - OWNER: a per-mission FSM instance watched over the "mission" stream.
  - INTAKE events: intent.accepted (module 3), task.completed / task.completion_refused
    (module 10), effect.* (module 8) folded via correlation_id.
  - Mind the loop: append -> observer reacts -> append -> ... The FSM must be
    EVENT-DRIVEN (pure fold of the log, like MemoryProjection.rebuild) or
    TAIL-FOLLOWING (low-watermark seq poll), never new events meaning new effects.
  - MUST pass service.observer into engines it constructs (F-E15 residual).
  - Compensation: declare the seam and the CompensationRecord shape now; the
    first real adapter/compensator lands with M2 effects, per §83 scope.

Determinism target (mirror NAT-03/G20):
  replay(log) twice -> identical mission state + digest. Cross-run digest NOT
  promised (payloads carry wall-clock timestamps) — document it.

Scope boundaries (do not build):
  - No agent-runtime loop, no scheduling, no budget enforcement (M2).
  - No manifest-DAG engine, no parallel mission graph.
  - No new effect types and no real adapters.
```

## 3. M1.1 entry conditions (gates)

1. M1 sign-off recorded — **DONE 2026-09-18**.
2. Model backend reachable (ADR-010: remote OpenAI-compatible / Groq, key set).
3. `main` pushed to `origin` / branch protection resolved.
4. Kernel invariant: modules 1–13 behavior unchanged by M1.1 (additive only).

## 4. Sequencing

1. **Ratify** the §2 contract above (creator)
2. **Implement** `mission_lifecycle.py` + tests (Big Pickle)
3. **Adversarial pass** (Freebuff) on the transition table + loop-safety
4. **Independent verify** (Antigravity)
5. **Creator gate** → M1.1 signed or M2 begins

---

## Paste-ready kickoff prompt (implementer)

Hand this to the implementation session verbatim.

```markdown
# Module 14 — deterministic mission-lifecycle FSM (STRETCH M1.1) — kickoff

You are Big Pickle (OpenCode), primary implementation engineer.
Baseline: `main @ HEAD`, 243 passed, modules 1-13 VERIFIED + creator-signed.

READ FIRST (re-derive from disk, trust nothing quoted):
- docs/MASTER_BUILD_SPEC.md §83, §127.1, §134.1 STRETCH (M1.1), §112 invariants
- src/jarvis/kernel/done_gate.py (the only task.completed path, NAT-05)
- src/jarvis/kernel/effect_envelope.py (single-effect envelope, module 8)
- src/jarvis/kernel/memory_projection.py (pure fold precedent for digesting state)
- src/jarvis/kernel/policy.py (DATA-table precedent for transitions)
- project_state.yaml (m1_e15_residual, m1_1_stretch, nats)

DELIVER:
1. Ratify or refine §2 contract (transition table AS DATA, pure fold, event intake
   list, compensation seam shape). If you must change the contract, say what/why.
2. Implement src/jarvis/kernel/mission_lifecycle.py + tests/kernel/test_mission_lifecycle.py
   Worktree branch task/m1.1-mod14; merge to main only when green.
3. MUST: pass service.observer into every EffectEnvelopeEngine built here (F-E15 residual).
4. MUST: consume — never emit — task.completed; refusal/completion are done-gate's only.
5. Determinism tests: replay twice -> identical state + digest; document cross-run
   NOT promised (wall-clock payloads, same rule as NAT-03/G20).
6. No hidden now()/RNG/network. No budget, no scheduling, no agent loop, no real effects.

Do not touch modules 1-13 behavior. Additive only. No history rewrites. No push.
```