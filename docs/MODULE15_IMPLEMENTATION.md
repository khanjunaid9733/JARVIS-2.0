# Module 15 — Model-Backed Answering (Implementation Note)

Ratifies the M1.1 STRETCH intent (spec §134.1) for the `say` question path.
Author: Big Pickle (OpenCode), 2026-09-18. Target: `main` @ `f89ad5f` +
CLI wiring @ `b45add7`. No Freebuff/Antigravity advisory pass yet — pending
handoff (`docs/M1_1_ADVERSARIAL_HANDOFF.md`).

## 1. What it adds

`jarvis.kernel.model_answer`:

- `StructuredAnswer` — the schema the gateway validates model output against
  ("jarvis.answer.v1"; `answer: str`, `confidence: float ∈ [0,1]`, `notes`).
- `answer_question(projection, question, *, gateway, log, principal_id,
  recall_limit, model_name)` — returns `ModelAnswerResult`:
  - gateway `None` → pure module-11 extractive path, **records nothing**
    (`recorded=False`, `fallback_reason="model_gateway_unavailable"`). This is
    the §127.1 byte-identical offline guarantee.
  - gateway present → exactly one `generate_structured` attempt. On
    `TypedFailure` falls back to the deterministic answer and appends
    `question.asked` with `fallback="deterministic"` + `failure_reason`.
    On success appends `fallback="model"` and returns the validated answer.
- `question.asked` audit event, stream `"session"`, `cause_event_id` =
  top recalled memory, appended ONLY on the gateway path.

## 2. The grounding correction (found in self-review before commit)

The first draft called `generate_structured` without any task input: the
module-6 seam has no prompt channel and the adapter hardcoded
`"Emit exactly one JSON object."` as the user message. The model could not
see the question. Verified live: it answered with a JSON-presence preamble.

**Fix — additive `input_text` seam** (F-E15 precedent: optional param,
default behavior unchanged):

- `ModelGateway.generate_structured(..., input_text=None)` — forwarded to
  adapter args **only when not None**, so existing module-6 callers pass
  byte-identical args.
- `OpenAICompatibleAdapter.invoke` — non-empty `args["input_text"]` becomes
  the user message; absent → the module-6 schema-conformance prompt, unchanged.
- `answer_question` builds `input_text` = question + recalled memories
  (source + `event_id` per hit) + an "answer using ONLY these memories"
  instruction.

Regression tests pin both halves of the seam (`test_input_text_forwarded_only_when_provided`,
`test_invoke_input_text_becomes_user_message`,
`test_invoke_without_input_text_uses_schema_conformance_prompt`) and the
grounding (`sent["input_text"]` contains the question AND the memory).

## 3. Model identity

The module-6 adapter default `llama-3.3-70b-versatile` is decommissioned on
Groq (HTTP 404; the backend now serves only `openai/gpt-oss-*`, `qwen`,
`compound`) — verified against the live `/models` listing. Module 15 does
not change module 6; the CLI seams select the model:

- `JARVIS_MODEL_NAME` env, default `openai/gpt-oss-120b`
  (`cli.DEFAULT_MODEL_NAME`), passed to the adapter and recorded as
  `question.asked.payload["model_name"]`.

## 4. Traceability / honesty seams

- `question.asked` payload: `question`, `prompt_id` ("jarvis.answer.v1"),
  `fallback` ("model" | "deterministic"), `provider_id`, `contract_id`,
  `contract_version`, `schema_sha256`, `model_name`, `attempts`,
  `tokens` (always `None` today — module-6 adapter does not surface `usage`),
  `failure_reason`, `recalled_memory_event_id`.
- `confidence` semantics differ by `used_model`: model-declared (schema-clamped)
  when the model answered; the lexical overlap score otherwise.
- Failures are typed (`TypedFailure.reason`), never raw provider exceptions.
- The module never imports a provider client; it only goes through `ModelGateway`.

## 5. Acceptance interplay (unchanged, verified)

Pre-M1.1 §127.1 sequence still passes byte-identical offline: `say` appends
nothing; `status` prints `replayed 8 events`; `replay --verify` OK. The CLI
tests pin the offline environment (`home` fixture delenvs the model vars) so
test outcomes never depend on a live backend across machines.

## Suite

288 passed (267 pre-M1.1 baseline + new module 15/16/17 + CLI + seam tests).

## 6. Post-audit reconciliation (Antigravity pass, 2026-09-18)

Findings from `docs/M1_1_AUDIT.md` (verdict `M1.1_RECONCILIATION_READY`):

| Finding | Severity | Resolution |
| :--- | :--- | :--- |
| F-M15-1 `question.asked` never carried `mission_id` — mission question costs folded onto the "session" slab instead of the mission's slab (§80.4) | MEDIUM | **Fixed** — additive `mission_id: str \| None = None` on `answer_question()` / `_record_question()`; stamped on the recorded event. `mission_id=None` = prior behavior. `test_mission_scoped_question_stamps_mission_id_for_budget` pins the fold to the mission slab (session slab stays absent). |