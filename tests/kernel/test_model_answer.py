from __future__ import annotations

"""Module 15 model-backed answering tests (STRETCH M1.1, §134.1).

Doubly-fake: the gateway is driven by scripted adapters (module-6 test
style), never a live backend. A memory is committed into a real EventLog so
the projection + `question.asked` accounting seam are exercised end-to-end.
"""

import pytest

from jarvis.kernel.event_log import Event, EventLog
from jarvis.kernel.memory_projection import MemoryProjection
from jarvis.kernel.model_answer import (
    ANSWER_SCHEMA_ID,
    QUESTION_ASKED,
    SESSION_STREAM_ID,
    StructuredAnswer,
    answer_question,
)
from jarvis.kernel.model_gateway import (
    ModelGateway,
    ProviderTransportError,
    RoleContract,
    TypedFailure,
    ValidatedOutput,
)
from jarvis.kernel.registry import CapabilityRegistry

pytestmark = pytest.mark.anyio


class _FixedClock:
    def __init__(self, ts: str = "2026-09-18T00:00:01.000Z") -> None:
        self._ts = ts

    def now_utc_iso(self) -> str:
        return self._ts


def _log(tmp_path, name: str = "log.db") -> EventLog:
    return EventLog(db_path=str(tmp_path / name), clock=_FixedClock())


def _commit_memory(log: EventLog, content: str = "the safe word is umbrella") -> str:
    return log.append(
        Event(
            stream_id="memory",
            event_type="memory.write.committed",
            principal_id="creator",
            payload={"content": content, "source": "session 1"},
        )
    )


def _projection(log: EventLog) -> MemoryProjection:
    return MemoryProjection.rebuild(log)


class _FakeAdapter:
    provider_id = "model.adapter"

    def __init__(self, outputs: list[dict]) -> None:
        self.outputs = list(outputs)
        self.invoked_args: list[dict] = []

    async def invoke(self, contract_id, version, args):
        self.invoked_args.append(args)
        if not self.outputs:
            return {}
        return self.outputs.pop(0)

    def health_check(self) -> bool:
        return True


class _FailingAdapter:
    provider_id = "model.adapter"

    async def invoke(self, contract_id, version, args):
        raise ProviderTransportError("boom")

    def health_check(self) -> bool:
        return True


def _gateway(adapter, registry=None) -> ModelGateway:
    registry = registry or CapabilityRegistry.seed_m1_defaults()
    return ModelGateway(resolver=registry, adapters={"model.adapter": adapter})


async def test_no_gateway_is_pure_deterministic_and_records_nothing(tmp_path):
    log = _log(tmp_path)
    memory_id = _commit_memory(log)
    assert memory_id

    result = await answer_question(_projection(log), "what is the safe word?")

    assert result.used_model is False
    assert result.recorded is False
    assert result.answered is True
    assert result.answer == "umbrella"
    assert result.provider_id is None
    assert result.fallback_reason == "model_gateway_unavailable"
    assert not any(
        event.event_type == QUESTION_ASKED for event in log.replay()
    ), "offline path must not append events (§127.1 event counts unchanged)"

    log.close()


async def test_model_path_validates_structured_answer_and_records(tmp_path):
    log = _log(tmp_path)
    memory_id = _commit_memory(log)
    adapter = _FakeAdapter([{"answer": "umbrella", "confidence": 0.9}])
    gateway = _gateway(adapter)

    result = await answer_question(
        _projection(log),
        "what is the safe word?",
        gateway=gateway,
        log=log,
        model_name="openai/gpt-oss-120b",
    )

    assert result.used_model is True
    assert result.recorded is True
    assert result.answered is True
    assert result.answer == "umbrella"
    assert result.confidence == 0.9
    assert result.provider_id == "model.adapter"
    assert result.event_id is not None
    assert result.memory_event_id == memory_id
    assert result.fallback_reason is None

    asked = [e for e in log.replay() if e.event_type == QUESTION_ASKED]
    assert len(asked) == 1
    event = asked[0]
    payload = event.payload
    assert event.stream_id == SESSION_STREAM_ID
    assert event.cause_event_id == memory_id
    assert payload["fallback"] == "model"
    assert payload["provider_id"] == "model.adapter"
    assert payload["contract_id"] == "model.generate_structured"
    assert payload["contract_version"] == "1.0.0"
    assert payload["prompt_id"] == ANSWER_SCHEMA_ID
    assert payload["schema_sha256"] is not None
    assert payload["attempts"] == 1
    assert payload["tokens"] is None
    assert payload["failure_reason"] is None
    assert payload["recalled_memory_event_id"] == memory_id
    assert payload["model_name"] == "openai/gpt-oss-120b"
    # Grounding: the model receives the question AND the recalled memory.
    sent = adapter.invoked_args[0]["input_text"]
    assert "what is the safe word?" in sent
    assert "the safe word is umbrella" in sent

    log.close()


async def test_transport_failure_falls_back_and_records_deterministic(tmp_path):
    log = _log(tmp_path)
    _commit_memory(log)
    gateway = _gateway(_FailingAdapter())

    result = await answer_question(
        _projection(log), "what is the safe word?", gateway=gateway, log=log
    )

    assert result.used_model is False
    assert result.recorded is True
    assert result.answered is True
    assert result.answer == "umbrella"
    assert result.fallback_reason == "transport_error"

    asked = [e for e in log.replay() if e.event_type == QUESTION_ASKED]
    assert asked[0].payload["fallback"] == "deterministic"
    assert asked[0].payload["failure_reason"] == "transport_error"

    log.close()


async def test_unbound_adapter_records_fallback_and_classifies_reason(tmp_path):
    log = _log(tmp_path)
    _commit_memory(log)
    # Seeded registry resolves provider_id "model.adapter", but no adapter is
    # bound -> TypedFailure(reason="adapter_error") -> recorded fallback.
    registry = CapabilityRegistry.seed_m1_defaults()
    gateway = ModelGateway(resolver=registry, adapters={})

    result = await answer_question(
        _projection(log), "what is the safe word?", gateway=gateway, log=log
    )

    assert result.used_model is False
    assert result.answered is True
    assert result.fallback_reason == "adapter_error"
    asked = [e for e in log.replay() if e.event_type == QUESTION_ASKED]
    assert asked and asked[0].payload["fallback"] == "deterministic"

    log.close()


async def test_unanswerable_question_reports_not_answered(tmp_path):
    log = _log(tmp_path)
    result = await answer_question(
        _projection(log), "what is the meaning of life?", log=log
    )
    assert result.answered is False
    assert result.answer is None
    assert result.recorded is False
    log.close()