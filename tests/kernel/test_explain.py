from __future__ import annotations

"""Module 17 full-explain renderer tests (STRETCH M1.1, §134.1).

Read-only folds over hand-built logs: cause chains, lifecycle state, model
provenance, recalled-memory scores, effect/policy counts, and budget slabs.
"""

import pytest

from jarvis.kernel.done_gate import CompletionGate
from jarvis.kernel.event_log import Event, EventLog
from jarvis.kernel.explain import explain_event
from jarvis.kernel.memory_projection import MemoryProjection
from jarvis.kernel.mission_lifecycle import (
    LIFECYCLE_COMPLETED,
    MISSION_STARTED,
    MISSION_STREAM_ID,
    MissionLifecycleOwner,
)
from jarvis.kernel.model_answer import QUESTION_ASKED, answer_question
from jarvis.kernel.model_gateway import ModelGateway
from jarvis.kernel.registry import CapabilityRegistry

pytestmark = pytest.mark.anyio


class _FixedClock:
    def __init__(self, ts: str = "2026-09-18T00:00:02.000Z") -> None:
        self._ts = ts

    def now_utc_iso(self) -> str:
        return self._ts


def _log(tmp_path, name: str = "log.db") -> EventLog:
    return EventLog(db_path=str(tmp_path / name), clock=_FixedClock())


def _memory_chain(tmp_path) -> tuple[EventLog, MemoryProjection, dict[str, str]]:
    """proposed -> verified -> committed chain; returns event ids per type."""
    log = _log(tmp_path)
    proposed = log.append(
        Event(stream_id="memory", event_type="memory.write.proposed",
              principal_id="creator", payload={"content": "the safe word is umbrella"})
    )
    verified = log.append(
        Event(stream_id="memory", event_type="memory.write.verified",
              principal_id="creator", cause_event_id=proposed,
              payload={"content": "the safe word is umbrella", "source": "session 1"})
    )
    committed = log.append(
        Event(stream_id="memory", event_type="memory.write.committed",
              principal_id="creator", cause_event_id=verified,
              payload={"content": "the safe word is umbrella", "source": "session 1"})
    )
    return log, MemoryProjection.rebuild(log), {"proposed": proposed, "verified": verified, "committed": committed}


class _FakeAdapter:
    provider_id = "model.adapter"

    def __init__(self, outputs: list[dict]) -> None:
        self.outputs = list(outputs)

    async def invoke(self, contract_id, version, args):
        return self.outputs.pop(0) if self.outputs else {}

    def health_check(self) -> bool:
        return True


def test_unknown_event_returns_none(tmp_path):
    log, _, _ = _memory_chain(tmp_path)
    assert explain_event(log, MemoryProjection.rebuild(log), "01NOSUCHULID0000000000000") is None
    log.close()


def test_memory_chain_cause_order_and_common_lines(tmp_path):
    log, projection, ids = _memory_chain(tmp_path)
    explanation = explain_event(log, projection, ids["committed"])

    assert explanation is not None
    assert explanation.event_type == "memory.write.committed"
    assert [link.event_id for link in explanation.chain] == [
        ids["committed"],
        ids["verified"],
        ids["proposed"],
    ]
    assert explanation.chain[-1].cause_event_id is None
    assert explanation.lifecycle_state is None
    assert explanation.lifecycle_transitions == []
    assert explanation.model_provenance is None
    assert explanation.memory_content == "the safe word is umbrella"
    assert explanation.memory_source == "session 1"
    assert explanation.capability_check_count == 0
    assert explanation.effect_count == 0
    assert explanation.budget is None, "no question.asked events -> no budget slab"
    log.close()


async def test_question_asked_explains_model_provenance_and_budget(tmp_path):
    log = _log(tmp_path)
    memory_id = log.append(
        Event(stream_id="memory", event_type="memory.write.committed",
              principal_id="creator",
              payload={"content": "the safe word is umbrella", "source": "session 1"})
    )
    projection = MemoryProjection.rebuild(log)
    registry = CapabilityRegistry.seed_m1_defaults()
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": _FakeAdapter([{"answer": "umbrella", "confidence": 0.9}])})
    result = await answer_question(projection, "what is the safe word?", gateway=gateway, log=log)
    assert result.event_id is not None

    explanation = explain_event(log, MemoryProjection.rebuild(log), result.event_id)

    assert explanation is not None
    assert explanation.model_provenance is not None
    assert explanation.model_provenance["fallback"] == "model"
    assert explanation.model_provenance["provider_id"] == "model.adapter"
    assert explanation.model_provenance["recalled_memory_event_id"] == memory_id
    assert explanation.recalled_memories
    assert explanation.recalled_memories[0].event_id == memory_id
    assert explanation.budget is not None
    assert explanation.budget.model_calls == 1
    assert explanation.budget.spent_tokens == 0
    log.close()


def test_mission_lifecycle_state_and_transitions_rendered(tmp_path):
    log = _log(tmp_path)
    log.append(
        Event(stream_id=MISSION_STREAM_ID, event_type=MISSION_STARTED,
              principal_id="creator", mission_id="m-1",
              payload={"objective": "x", "budget": {"tokens": 20000}})
    )
    owner = MissionLifecycleOwner(log, mission_id="m-1")
    owner.advance()  # executing; lifecycle.accepted appended
    CompletionGate(log, principal_id="creator").declare_completion(
        task_id="t-1",
        evidence={"artifact": {"result": "ok"}, "verification": "verified by test"},
        mission_id="m-1",
    )
    owner.advance()  # completed; lifecycle.completed appended

    target_id = max(
        (e.event_id for e in log.replay()
         if e.event_type == LIFECYCLE_COMPLETED),
        default=None,
    )
    assert target_id is not None

    explanation = explain_event(log, MemoryProjection.rebuild(log), target_id)
    assert explanation is not None
    assert explanation.lifecycle_state == "completed"
    assert LIFECYCLE_COMPLETED in explanation.lifecycle_transitions
    assert explanation.budget is not None
    assert explanation.budget.allocation_tokens == 20000
    assert explanation.budget.stream_id == "m-1"
    log.close()


def test_effect_and_policy_events_are_counted(tmp_path):
    log = _log(tmp_path)
    log.append(
        Event(stream_id="effect", event_type="effect.prepared", principal_id="creator",
              mission_id="m-2", payload={"effect_id": "fx-1"})
    )
    log.append(
        Event(stream_id="effect", event_type="effect.committed", principal_id="creator",
              mission_id="m-2", cause_event_id=None, payload={"effect_id": "fx-1"})
    )
    log.append(
        Event(stream_id="policy", event_type="policy.check", principal_id="creator",
              mission_id="m-2", payload={"policy_result": "allow"})
    )
    log.append(
        Event(stream_id="effect", event_type="effect.verified", principal_id="creator",
              mission_id="m-2", cause_event_id=None, payload={"effect_id": "fx-1"})
    )
    target = max((e.event_id for e in log.replay()), default=None)
    assert target is not None

    explanation = explain_event(log, MemoryProjection.rebuild(log), target)
    assert explanation is not None
    assert explanation.effect_count == 1
    assert explanation.capability_check_count == 1
    log.close()