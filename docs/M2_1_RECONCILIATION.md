# M2.1 Reconciliation — Antigravity Audit + Freebuff Red-Team

**Target:** `task/m2.1` @ `af99696` → reconciled on the task branch.
**Reconcilers:** Big Pickle (implementation); Antigravity (independent verify);
Freebuff (adversarial red-team).
**Suite after reconciliation:** **332 passed** (312 base + 20 red-team probes).
**Date:** 2026-09-19

## 1. Antigravity findings (`docs/M2_1_AUDIT.md`) — all RESOLVED

| ID | Sev | Resolution | Regression test |
| :-- | :-- | :-- | :-- |
| `F-M2.1-1` | MEDIUM | `record_episodic(..., mission_id=None)` forwarded to `Event.mission_id` | `test_trace_stamps_mission_id` |
| `F-M2.1-2` | MEDIUM | Clamp only true numerics (`isinstance(confidence,(int,float)) and not isinstance(confidence,bool)`); non-numeric/bool left verbatim so the frozen `DoneGate` (`confidence_valid`) rejects them as typed `TraceWriteResult(status="rejected")` — no raise | `test_non_numeric_confidence_is_rejected_typed` (+ Freebuff A5/A6) |
| `F-M2.1-3` | LOW | `Memory.get()` uses explicit `is not None` lookup instead of `or`-chaining | `test_get_returns_empty_memory_payload_not_none` (+ Freebuff C2) |
| `F-M2.1-4` | LOW | `Memory.__init__` always materialises both `_index` and `_projection` slots | `test_backend_slots_always_materialized` (+ Freebuff C3) |
| `F-M2.1-5` | LOW | Evidence tests refactored to `pytest.raises` idioms | — |

## 2. Freebuff findings (`docs/M2_1_REDTEAM_FB.md`) — code fixes RESOLVED

| FB ID | Sev | Resolution |
| :-- | :-- | :-- |
| `F-M2.1-FB-3` (A1) | MEDIUM | Bare `str`/`bytes` `evidence` is one reference, never char-split; `cause_event_id` stays the whole id |
| `F-M2.1-FB-4` (A3) | MEDIUM | `TraceWriteResult.correlation_id` added + populated (contract item B); `gate` is now `GateDecision \| None` |
| `F-M2.1-FB-5` (A2) | LOW | Non-sequence `evidence` → typed `TraceWriteResult(status="rejected", gate=None)`, no `TypeError` |
| `F-M2.1-FB-8` (C4) | LOW | `Memory.recall(limit=...)` rejects non-positive / non-int / bool limits with `ValueError` |
| `F-M2.1-FB-9` (D1) | LOW | `_cmd_recall` collapses embedded newlines so one hit = one line |
| `F-M2.1-FB-7` | LOW | `docs/M2_1_AUDIT.md` verdict reworded (additive `cli.py` made explicit; frozen modules 1–17 byte-identical) |

Freebuff A5/A6 (the two faces of `F-M2.1-2`) were closed by the same guard; A7/D2/D3 were no-findings
(kept as regression pins).

## 3. Creator rulings requested (NOT code changes)

Recommended to resolve at the M2.1 merge gate, before M2.2/M2.10 build on these surfaces:

1. **`F-M2.1-FB-1` — recall cannot distinguish verified memory from raw trace (MEDIUM).**
   `RecalledMemory` is a frozen module-11 type; adding `tier`/`kind` there breaks the freeze. Two sanctioned
   options: (a) additive M2.1-ranked-hit type carrying `tier` (`memory`/`trace`) + `verified` from the fold maps,
   changing the facade's return type (contract C extension, needs ratification); or (b) defer to M2.2 when the
   rerank seam replaces lexical `recall()` as the consumed boundary. **Recommendation: (b) defer to M2.2**, keep
   M2.1 contract stable; track it in M2.2 scope.
2. **`F-M2.1-FB-2` — one log, two "canonical" digests (MEDIUM).** `MemoryIndex.digest()` and module-7
   `MemoryProjection.digest()` hash different state shapes; the M2 digest is blind to provider identity.
   **Recommendation: declare `MemoryIndex.digest()` the single NAT-03 digest for the memory tract at M2.10
   (fold `providers` in when M2.10 recovery consumes it)**; document that module-7's is the frozen M1 ledger
   digest. This is a ledger/`project_state.yaml` decision.
3. **`F-M2.1-FB-6` (A4) — a refused trace leaves no log entry (LOW).** Contract-compliant (`§3 B`: no event on
   gate failure) but asymmetric with module-10's `memory.write.rejected`. **Recommendation: accept the asymmetry
   and document it** (traces are raw, non-promoted records; refusal auditability returns with M2.4 verification
   ladder). Adding `memory.trace.rejected` would change `MemoryIndex` folding (a digest input) — not worth it now.

## 4. Evidence retained

- `tests/review/test_freebuff_redteam_m2_1.py` — 20 behavior probes; the `# FLIPS ON FIX` assertions were flipped
  to assert the reconciled behavior, turning them into regression pins.
- `docs/M2_1_AUDIT.md`, `docs/M2_1_REDTEAM_FB.md`, `docs/M2_1_REDTEAM_PROMPT_FB.md` — audit + red-team records.