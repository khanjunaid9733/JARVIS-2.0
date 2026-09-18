from __future__ import annotations

"""`jarvis.*` span emission (module 12, spec §110 / §110.1).

"Every event is a span. Every model call, effect, and verification is a
child" (§110.1). This module provides the emission seam:

- `Observer` — a minimal Protocol (`span(name, attributes)` context manager).
- `NoOpObserver` — the default; every kernel module stays inert when no
  observer is supplied (no behavior change, no dependency at import time).
- `OtelObserver` / `configure_otel()` — real OpenTelemetry tracing. The
  `opentelemetry` import is lazy (inside `configure_otel`), so importing the
  kernel never requires the SDK.

Span names and attribute keys are DATA (constants below), exactly as §110.1
tabulates. Instrumentation is ADDITIVE and optional: `EventLog`,
`PolicyEngine`, `ModelGateway`, and `EffectEnvelopeEngine` accept
`observer=None` and are unchanged when it is not provided. The effect
pipeline emits a `jarvis.effect.execute` span per run with the postcondition
check under `jarvis.verify.postconditions` (F-E15): with an observer
attached, every event is a span and every effect/verification is a child as
§110.1 requires. Exported spans require an exporter — attach one for durable
tracing; the NoOp default stays inert.
"""

from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Protocol, runtime_checkable

SPAN_EVENT = "jarvis.event"
SPAN_MODEL_CALL = "jarvis.model.call"
SPAN_POLICY_CHECK = "jarvis.policy.check"
SPAN_REGISTRY_RESOLVE = "jarvis.registry.resolve"

EFFECT_SPAN_PREFIX = "jarvis.effect."
VERIFY_SPAN_PREFIX = "jarvis.verify."


def effect_span_name(name: str) -> str:
    return f"{EFFECT_SPAN_PREFIX}{name}"


def verify_span_name(name: str) -> str:
    return f"{VERIFY_SPAN_PREFIX}{name}"


@runtime_checkable
class SpanHandle(Protocol):
    def set_attribute(self, key: str, value: Any) -> None: ...


class Observer(Protocol):
    def span(
        self, name: str, attributes: Mapping[str, Any] | None = None
    ) -> Any: ...


class _NoOpSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        return None


class NoOpObserver:
    """Default observer: records nothing."""

    @contextmanager
    def span(
        self, name: str, attributes: Mapping[str, Any] | None = None
    ) -> Iterator[SpanHandle]:
        yield _NoOpSpan()


class OtelObserver:
    """Wraps a real `opentelemetry.trace.Tracer`."""

    def __init__(self, tracer: Any) -> None:
        self._tracer = tracer

    @contextmanager
    def span(
        self, name: str, attributes: Mapping[str, Any] | None = None
    ) -> Iterator[SpanHandle]:
        with self._tracer.start_as_current_span(
            name, attributes=dict(attributes or {})
        ) as span:
            yield span


def configure_otel(*, exporter: Any = None, service_name: str = "jarvis") -> OtelObserver:
    """Build an `OtelObserver`. Without an exporter, spans are collected then
    dropped (still valid tracing; attach an exporter for durable spans)."""
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    provider = TracerProvider(
        resource=Resource.create({"service.name": service_name})
    )
    if exporter is not None:
        provider.add_span_processor(SimpleSpanProcessor(exporter))
    return OtelObserver(provider.get_tracer("jarvis"))


def event_attributes(event: Any) -> dict[str, Any]:
    """Required §110.1 attributes for a `jarvis.event` span."""
    attributes: dict[str, Any] = {
        "event.id": event.event_id,
        "principal.id": event.principal_id,
        "event.type": event.event_type,
    }
    if event.mission_id is not None:
        attributes["mission.id"] = event.mission_id
    if event.task_id is not None:
        attributes["task.id"] = event.task_id
    return attributes
