from __future__ import annotations

"""Module 12 `jarvis.*` span emission tests (spec §110 / §110.1)."""

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from pydantic import BaseModel

from jarvis.kernel.event_log import Event, EventLog
from jarvis.kernel.intent import Budget, Manifest
from jarvis.kernel.model_gateway import ModelGateway, RoleContract, ValidatedOutput
from jarvis.kernel.policy import AutonomyLevel, PolicyContext, PolicyEngine
from jarvis.kernel.registry import CapabilityRegistry
from jarvis.observability import (
    SPAN_EVENT,
    SPAN_MODEL_CALL,
    SPAN_POLICY_CHECK,
    SPAN_REGISTRY_RESOLVE,
    NoOpObserver,
    configure_otel,
    effect_span_name,
    verify_span_name,
)

pytestmark = pytest.mark.anyio


def _observer() -> tuple[object, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    return configure_otel(exporter=exporter), exporter


def _names(exporter: InMemorySpanExporter) -> list[str]:
    return [span.name for span in exporter.get_finished_spans()]


def _attributes(exporter: InMemorySpanExporter, name: str) -> dict:
    for span in exporter.get_finished_spans():
        if span.name == name:
            return dict(span.attributes or {})
    raise AssertionError(f"span {name!r} not emitted")


def test_span_name_helpers():
    assert effect_span_name("fs.read") == "jarvis.effect.fs.read"
    assert verify_span_name("fs.read") == "jarvis.verify.fs.read"


def test_event_append_emits_jarvis_event_span(tmp_path):
    observer, exporter = _observer()
    log = EventLog(db_path=str(tmp_path / "log.db"), observer=observer)

    log.append(
        Event(
            stream_id="memory",
            event_type="memory.write.committed",
            principal_id="creator",
            mission_id="m1",
            task_id="t1",
            payload={"content": "x"},
        )
    )

    assert SPAN_EVENT in _names(exporter)
    attrs = _attributes(exporter, SPAN_EVENT)
    assert attrs["principal.id"] == "creator"
    assert attrs["event.type"] == "memory.write.committed"
    assert attrs["mission.id"] == "m1"
    assert attrs["task.id"] == "t1"
    assert attrs["event.id"]


def test_noop_observer_is_inert(tmp_path):
    log = EventLog(db_path=str(tmp_path / "log.db"), observer=NoOpObserver())
    assert log.append(Event(stream_id="s", event_type="e", principal_id="creator"))


def test_policy_check_emits_span():
    observer, exporter = _observer()
    engine = PolicyEngine(observer=observer)
    manifest = Manifest(
        manifest_id="m",
        intent_id="i",
        contracts=[],
        required_capabilities=[],
        budget=Budget(),
        constraints={},
        risk_class="safe",
        manifest_sha256="0" * 64,
        created_at_utc="2026-09-18T00:00:00Z",
    )
    context = PolicyContext(
        principal_id="creator",
        granted_capabilities=frozenset(),
        autonomy_level=AutonomyLevel.L4,
    )

    engine.evaluate(manifest, context)

    attrs = _attributes(exporter, SPAN_POLICY_CHECK)
    assert attrs["policy.result"] == "allow"
    assert attrs["principal.id"] == "creator"
    assert not list(attrs.get("capability.requested", []))


async def test_model_gateway_emits_registry_and_model_spans():
    observer, exporter = _observer()

    class Out(BaseModel):
        value: int

    class FakeAdapter:
        provider_id = "model.adapter"

        async def invoke(self, contract_id: str, version: str, args: dict) -> dict:
            return {"value": 7}

        def health_check(self) -> bool:
            return True

    registry = CapabilityRegistry.seed_m1_defaults()
    gateway = ModelGateway(
        registry, {"model.adapter": FakeAdapter()}, observer=observer
    )

    result = await gateway.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Out)

    assert isinstance(result, ValidatedOutput)
    assert result.value.value == 7
    names = _names(exporter)
    assert SPAN_REGISTRY_RESOLVE in names
    assert SPAN_MODEL_CALL in names
    assert _attributes(exporter, SPAN_REGISTRY_RESOLVE)["provider.id"] == "model.adapter"
    assert _attributes(exporter, SPAN_MODEL_CALL)["model.name"] == "model.adapter"
