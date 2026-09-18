# M1.1 Freeze & Sign-off

**Status:** FROZEN — creator-signed.
**Date:** 2026-09-18.
**Freeze target:** `main` @ `160a3c2` (reconciliation of the M1.1 audit).
**Owner:** Big Pickle (OpenCode) — implementation; Antigravity — verification.
**Baseline:** M1 signed off 2026-09-18 (`m1_signoff: creator_signed_off_2026-09-18`).

## 1. Scope frozen

- **M1 (modules 1–13):** MUST-tier vertical slice — event store, creator
  identity, intent ABI, capability registry + provider adapter interface,
  model gateway + `generate_structured`, minimal memory projection,
  CLI `init/say/explain`, deterministic replay + `replay --verify`,
  OTel `jarvis.*` spans, NAT-01…05.
- **M1.1 STRETCH (modules 14–17):**
  - module 14 — deterministic mission-lifecycle FSM (`mission_lifecycle.py`)
  - module 15 — model-backed structured answering (`model_answer.py`)
  - module 16 — budget accounting ledger (`budget_ledger.py`)
  - module 17 — full `explain` cause-chain rendering (`explain.py`)

## 2. Acceptance evidence

- **Suite:** 292 passed (267 pre-M1.1 baseline; zero regressions to
  modules 1–13; +25 M1.1/reconcile tests).
- **Adversarial review (module 14):** F-M14-1..6 — 5 fixed @ `f31f87f`,
  1 accepted + documented (`docs/MODULE14_IMPLEMENTATION.md` §7).
- **Independent audit (modules 15–17):** Antigravity, verdict
  `M1.1_RECONCILIATION_READY` (`docs/M1_1_AUDIT.md` @ `46e0d98`).
  Findings F-M15-1, F-M16-1, F-M17-1, F-M17-2 all fixed + regression
  tested @ `160a3c2` — see `docs/MODULE15/16/17_IMPLEMENTATION.md`.
- **Live backend:** Groq-path `say`/`explain` verified end-to-end
  (grounded answer, model-name provenance, budget slab, `replay --verify`
  OK) against an isolated `JARVIS_HOME`.
- **Offline determinism:** §127.1 transcript still byte-identical on a
  fresh machine with no backend configured (`status` reports 8 events;
  `say` is deterministic; `explain` renders the full blocks; `replay
  --verify` OK).

## 3. Frozen implementation invariant

From this point, `src/` for modules 1–17 is FROZEN until a ratified M2 or
later requirement changes it. Changes require an approved design
(`project_state.yaml` truth protocol: VISION → PROPOSAL → ACCEPTED_DESIGN →
IMPLEMENTED → VERIFIED) and remain additive-first.

## 4. Open residuals (recorded, NOT blockers)

1. **Manifest-DAG validation** — the 4th §134.1 STRETCH item
   ("manifest DAG validation (full dependency-graph checks)") was NOT built
   in M1.1; `intent-to-manifest compilation` is an M2 work package (§M2,
   `MASTER_BUILD_SPEC.md:4961-4969`). Carried forward, not dropped.
2. **Key-based authority (NAT-02 second half)** — signature verification
   deferred to the M2 authority module; M1 trust model = `principal_id`
   equality remains in force (§127.1, state `nat_02`).
3. **Token accounting** — adapters do not surface `usage` yet; budget
   display is "0 tokens accounted" honestly. M2 budgets/rate-limits work
   packages consume the `tokens` payload seam.
4. **Model identity** — module-6 adapter default `llama-3.3-70b-versatile`
   is decommissioned on Groq; the M1.1 CLI consumer selects the model via
   `JARVIS_MODEL_NAME` (default `openai/gpt-oss-120b`). Module 6 itself is
   unchanged.
5. **Environment** — Groq key/base URL are set at User scope; repository
   visibility is subject to the creator's choice (public/private).

## 5. M1.1 sign-off

Ratified on 2026-09-18 by the creator: **M1.1 is SIGNED OFF and FROZEN.**
Milestone 2 (Memory OS) may begin per `docs/M2_KICKOFF.md`.