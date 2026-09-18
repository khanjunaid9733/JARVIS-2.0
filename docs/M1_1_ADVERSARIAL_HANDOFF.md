# M1.1 Adversarial Review Handoff — Modules 15/16/17 (Antigravity)

Frozen target: **`main` @ `b45add7`** (kernel `f89ad5f` + CLI `b45add7`).
Reviewer: Antigravity (independent verifier). Author of the changes: Big
Pickle (OpenCode). Prior art: module 14 adversarial pass (`docs/MODULE14_IMPLEMENTATION.md` §7).

The goal: adversarial review of the M1.1 STRETCH completion (model-backed
say, budget accounting, full explain rendering) before sign-off. Verify
state against the repo, find flaws, and file findings. **Do not modify
`src/` or `tests/`** — this is a read-only review; findings go in the
report.

## Context (trust but verify)

- M1 MUST tier is signed off and dual-verified. M1.1 is additive-only: no
  behavior changes to modules 1–13 when M1.1 features are disabled.
- The §127.1 acceptance transcript must stay byte-identical on a fresh,
  offline machine: after init+remember, `status` reports `replayed 8
  events`; `say "what is the safe word?"` prints `umbrella` with the
  deterministic disclosure; `replay --verify` OK.
- The machine may have `JARVIS_MODEL_API_KEY`/`JARVIS_MODEL_BASE_URL` set
  at User scope. When they are set, `say` routes through the live Groq
  gateway and appends ONE `question.asked` event. The CLI tests now
  delenv those vars (hermetic), so the suite must pass regardless.
- Model identity: the module-6 adapter default `llama-3.3-70b-versatile` is
  decommissioned on Groq; M1.1 picks `JARVIS_MODEL_NAME` (default
  `openai/gpt-oss-120b`) at the CLI seam and records `model_name` on
  `question.asked`.

## Review targets

### T1 — Additive `input_text` seam (the one module-6 touching change)
Files: `src/jarvis/kernel/model_gateway.py` (`generate_structured`),
`src/jarvis/providers/openai_compatible.py` (`invoke`).
Verify: (a) args identical when `input_text=None` (no callers broken);
(b) the user message switches only when a non-empty string is present;
(c) no secret/error path changed; (d) offline byte-compat holds
(`test_section_127_1_acceptance_sequence`).

### T2 — Module 15 (`src/jarvis/kernel/model_answer.py`)
- `question.asked` appended ONLY on the gateway path, including the
  deterministic-fallback-with-recorded-failure path; the pure no-gateway
  path appends NOTHING (spot-check the interactive smoke, §127.1).
- Payload fields (`fallback`, `provider_id`, `contract_id`, `contract_version`,
  `schema_sha256`, `model_name`, `attempts`, `tokens: None`,
  `failure_reason`, `recalled_memory_event_id`) are honored and read-only.
- `confidence` semantics differ by `used_model` — is the CLI disclosure
  honest on both paths?
- Grounding: the model receives question + recalled memories, not a bare
  conformance prompt.

### T3 — Module 16 (`src/jarvis/kernel/budget_ledger.py`)
- `BudgetLedger.rebuild` folds `question.asked` (mission_id-else-stream key)
  and `mission.started` allocation; per-mission keying matches §80.4.
- Honest accounting: `spent_tokens` never fabricated; non-int / negative
  token values ignored; `allocation` renders "unbounded" when unset.
- No clock/RNG/writes; identical logs → identical ledgers.

### T4 — Module 17 (`src/jarvis/kernel/explain.py`) + CLI
(`src/jarvis/cli.py`: `_build_model_gateway`, `_answer_question`,
`_cmd_say`, `_cmd_explain`)
- Pure read-only renderer; never calls a model; §127.1 assertion strings
  (`cause chain: …`, `memory content: '…'`) intact.
- Cause-chain walk integrity (cycles? long chains? unknown ids → None).
- Lifecycle block computed only for mission-tagged targets.
- CLI: `getattr(result, "used_model", False)` keeps the offline
  `AnswerResult` path crash-free. `_build_model_gateway` never leaks the
  API key and never leaves an environment without a provider in a broken
  state.

### T5 — Hermetic test hygiene
`tests/test_cli.py::home` delenvs the model vars; offline tests must not
depend on machine env. Adversarial: what happens on a machine where the
vars ARE set and the backend is unreachable — does `jarvis say` still work
(typed fallback), and do tests stay green?

## Verification commands (pwsh, `workdir: F:\JARVIS2.0`)

```pwsh
uv run --with pytest --with opentelemetry-sdk --with opentelemetry-api --with anyio pytest -q   # expect 288 passed
$env:JARVIS_HOME = "$env:TEMP\opencode\jarvis-adv"   # isolated smoke
Remove-Item -Recurse -Force $env:JARVIS_HOME -EA SilentlyContinue
uv run python -m jarvis init ; uv run python -m jarvis say "remember: the safe word is umbrella" ; uv run python -m jarvis say "what is the safe word?"
```

## Deliverable

A findings list numbered `F-M15.x` / `F-M16.x` / `F-M17.x` with severity
(CRITICAL/HIGH/MEDIUM/LOW), file:line, reproduction, and a proposed fix.
Explicitly state which findings are accepted-and-documented vs fixed.
Report the checked-out hash you audited when you report.