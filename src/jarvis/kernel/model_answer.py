from __future__ import annotations

"""Model-backed structured answering (module 15, STRETCH M1.1, spec §134.1).

The §127.1 smoke test's `say` question path is deterministic/extractive
("umbrella" from a lexical recall — disclosed). M1.1 adds the REAL
model-backed answer path: the question and its recalled memories are routed
through `ModelGateway.generate_structured` (module 6, ADR-006) to produce a
schema-validated `StructuredAnswer`. The deterministic path stays as the
fallback, so the acceptance gate remains reproducible on a fresh machine
with no backend configured.

Traceability, accounting, and honesty seams (all additive):

- A `question.asked` event (stream "session") is appended ONLY on the
  gateway path — whether the model answered ("model") or the call failed
  and fell back to the deterministic extractive answer ("deterministic").
  The pure no-gateway path appends NOTHING, so the §127.1 event counts
  (8 events after init + remember) are byte-identical offline.
- `question.asked` carries provider/contract/schema provenance plus
  `attempts` and the `TypedFailure.reason` when the call failed — the data
  source for `explain` provenance (§134.1 cause-chain rendering) and the
  budget ledger (module 16, §80.4).
- `tokens` is RESERVED in the payload and always `None` today: the module-6
  OpenAI-compatible adapter returns only `choices[0].message.content` and
  does not surface `usage` (a behavior change to module 6 the M1.1 kernel
  invariant forbids). Token accounting is therefore honest "0 accounted"
  until an adapter reports usage (M2). Disclosed in the module-15 report.

Role → schema is DATA (`StructuredAnswer` only; future roles register new
schemas beside it). The module never touches a provider client directly; it
goes through `ModelGateway` (ADR-001 seam). Failures are typed
(`TypedFailure`) and never leak raw provider exceptions.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .event_log import Event, EventLog
from .memory_projection import MemoryProjection
from .memory_query import answer as _deterministic_answer
from .memory_query import recall
from .model_gateway import ModelGateway, RoleContract, TypedFailure, ValidatedOutput
from .registry import CREATOR_PRINCIPAL_ID

SESSION_STREAM_ID = "session"
QUESTION_ASKED = "question.asked"
ANSWER_SCHEMA_ID = "jarvis.answer.v1"

_DEFAULT_RECALL_LIMIT = 2


class StructuredAnswer(BaseModel):
    """Schema the gateway validates model output against (ADR-006).

    Confidence is model-declared and clamped by the schema validator to
    [0, 1]; it is NOT the lexical score the deterministic path reports —
    `ModelAnswerResult.confidence` semantics differ by `used_model`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    answer: str = Field(..., description="direct answer to the question")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: str = Field(default="", description="optional free-form reasoning text")


class ModelAnswerResult(BaseModel):
    """One honest answering outcome.

    `used_model` distinguishes model-grounded from deterministic answers;
    `recorded` tells whether a `question.asked` event was appended;
    `confidence` is the model-declared value when `used_model`, else the
    lexical overlap score (same semantics as `memory_query.AnswerResult`).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    used_model: bool
    recorded: bool
    answered: bool
    answer: str | None
    confidence: float
    source: str | None  # deterministic: memory source; model: provider_id
    memory_event_id: str | None
    event_id: str | None
    provider_id: str | None
    fallback_reason: str | None


async def answer_question(
    projection: MemoryProjection,
    question: str,
    *,
    gateway: ModelGateway | None = None,
    log: EventLog | None = None,
    principal_id: str = CREATOR_PRINCIPAL_ID,
    recall_limit: int = _DEFAULT_RECALL_LIMIT,
    model_name: str | None = None,
    mission_id: str | None = None,
) -> ModelAnswerResult:
    """Answer a question, preferring the model-backed path when a gateway is
    available and resolving cleanly; falling back to the deterministic
    extractive answer otherwise.

    Pure path (gateway is None): byte-identical to module-11 behavior, no
    events appended, never awaits a provider. Gateway path: one
    `generate_structured` attempt; any `TypedFailure` falls back and is
    recorded as a `question.asked` event with `fallback="deterministic"`.
    """
    question = (question or "").strip()

    if gateway is None:
        res = _deterministic_answer(projection, question)
        return ModelAnswerResult(
            used_model=False,
            recorded=False,
            answered=res.answered,
            answer=res.answer,
            confidence=res.confidence,
            source=res.source,
            memory_event_id=res.memory_event_id,
            event_id=None,
            provider_id=None,
            fallback_reason="model_gateway_unavailable",
        )

    hits = recall(projection, question, limit=max(recall_limit, 1))
    context = "\n".join(
        f"- [{hit.source} | {hit.event_id}] {hit.content}" for hit in hits
    ) or "(no recalled memories)"
    top_memory_id = hits[0].event_id if hits else None

    input_text = (
        f"Question: {question}\n\n"
        f"Recalled memories:\n{context}\n\n"
        "Answer the question using ONLY the recalled memories above. "
        "If they do not contain the answer, say so plainly."
    )

    out = await gateway.generate_structured(
        RoleContract.SCHEMA_CONSTRAINED,
        StructuredAnswer,
        schema_id=ANSWER_SCHEMA_ID,
        task_id=None,
        input_text=input_text,
    )

    if isinstance(out, TypedFailure):
        res = _deterministic_answer(projection, question)
        event_id = _record_question(
            log,
            question=question,
            fallback="deterministic",
            provider_id=None,
            contract_id=None,
            contract_version=None,
            schema_sha256=None,
            attempts=out.attempts,
            failure_reason=out.reason,
            recalled_event_id=top_memory_id,
            principal_id=principal_id,
            model_name=model_name,
            mission_id=mission_id,
        )
        return ModelAnswerResult(
            used_model=False,
            recorded=event_id is not None,
            answered=res.answered,
            answer=res.answer,
            confidence=res.confidence,
            source=res.source,
            memory_event_id=res.memory_event_id,
            event_id=event_id,
            provider_id=None,
            fallback_reason=out.reason,
        )

    assert isinstance(out, ValidatedOutput)
    value = out.value
    assert isinstance(value, StructuredAnswer)
    event_id = _record_question(
        log,
        question=question,
        fallback="model",
        provider_id=out.provider_id,
        contract_id=out.contract_id,
        contract_version=out.contract_version,
        schema_sha256=out.schema_sha256,
        attempts=out.attempts,
        failure_reason=None,
        recalled_event_id=top_memory_id,
        principal_id=principal_id,
        model_name=model_name,
        mission_id=mission_id,
    )
    return ModelAnswerResult(
        used_model=True,
        recorded=event_id is not None,
        answered=True,
        answer=value.answer,
        confidence=value.confidence,
        source=out.provider_id,
        memory_event_id=top_memory_id,
        event_id=event_id,
        provider_id=out.provider_id,
        fallback_reason=None,
    )


def _record_question(
    log: EventLog | None,
    *,
    question: str,
    fallback: str,
    provider_id: str | None,
    contract_id: str | None,
    contract_version: str | None,
    schema_sha256: str | None,
    attempts: int,
    failure_reason: str | None,
    recalled_event_id: str | None,
    principal_id: str,
    model_name: str | None = None,
    mission_id: str | None = None,
) -> str | None:
    """Append the `question.asked` audit event. Returns its id or None when
    no log is attached (in-memory seam, modules 6/9/14 precedent).

    Mission-scoped questions stamp `mission_id` on the event (F-M15-1) so the
    budget ledger (module 16) folds the cost onto the mission's slab (§80.4)
    instead of the session slab; `mission_id=None` keeps module-15 behavior
    with no mission context.
    """
    if log is None:
        return None
    payload: dict[str, Any] = {
        "question": question,
        "prompt_id": ANSWER_SCHEMA_ID,
        "fallback": fallback,
        "provider_id": provider_id,
        "contract_id": contract_id,
        "contract_version": contract_version,
        "schema_sha256": schema_sha256,
        "model_name": model_name,
        "attempts": attempts,
        "tokens": None,
        "failure_reason": failure_reason,
        "recalled_memory_event_id": recalled_event_id,
    }
    event_id = log.append(
        Event(
            stream_id=SESSION_STREAM_ID,
            event_type=QUESTION_ASKED,
            principal_id=principal_id,
            mission_id=mission_id,
            cause_event_id=recalled_event_id,
            payload=payload,
        )
    )
    return event_id