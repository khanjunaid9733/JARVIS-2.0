from __future__ import annotations

"""Module 8 effect envelope tests (§83 / §98). Fakes only; no live effects.

The envelope is exercised against a seeded registry and scriptable fake
adapters. No network, no filesystem, no terminal effect ever executes.
"""

import pytest

from jarvis.kernel.effect_envelope import (
    EffectEnvelope,
    EffectEnvelopeEngine,
    EffectFailure,
)
from jarvis.kernel.event_log import EventLog
from jarvis.kernel.intent import Budget, Manifest, ResolvedContract
from jarvis.kernel.registry import CapabilityRegistry

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Fakes / helpers
# ---------------------------------------------------------------------------

class SpyAdapter:
    """Scriptable ProviderAdapter that counts invocations."""

    def __init__(self, provider_id, result=None, raises=None):
        self._provider_id = provider_id
        self.result = {"ok": True} if result is None else result
        self.raises = raises
        self.calls = 0

    @property
    def provider_id(self):
        return self._provider_id

    async def invoke(self, contract_id, version, args):
        self.calls += 1
        if self.raises is not None:
            raise self.raises
        return self.result

    def health_check(self):
        return True


def _manifest(
    contract_id="fs.read",
    *,
    version="1.0.0",
    required=("fs.read",),
    args=None,
):
    return Manifest(
        manifest_id="manifest-1",
        intent_id="intent-1",
        contracts=[
            ResolvedContract(
                id=contract_id, version=version, args=dict(args or {})
            )
        ],
        required_capabilities=list(required),
        budget=Budget(),
        constraints={},
        risk_class="safe",
        manifest_sha256="0" * 64,
        created_at_utc="2026-09-18T00:00:00Z",
    )


def _engine(adapters, *, log=None):
    return EffectEnvelopeEngine(
        CapabilityRegistry.seed_m1_defaults(), adapters, log=log
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

async def test_success_returns_verified_envelope():
    adapter = SpyAdapter("fs.default")
    engine = _engine({"fs.default": adapter})

    result = await engine.run(
        _manifest(),
        "fs.read",
        intended_change={"path": "/tmp/x"},
        postconditions={"ok": True},
        idempotency_key="k-success",
    )

    assert isinstance(result, EffectEnvelope)
    assert result.verification.passed is True
    assert result.provider_id == "fs.default"
    assert result.contract_id == "fs.read"
    assert result.contract_version == "1.0.0"
    assert result.manifest_id == "manifest-1"
    assert result.duplicate is False
    assert adapter.calls == 1


async def test_no_postconditions_is_verified_by_default():
    adapter = SpyAdapter("fs.default")
    engine = _engine({"fs.default": adapter})

    result = await engine.run(
        _manifest(), "fs.read", intended_change={}, idempotency_key="k-empty-post"
    )

    assert isinstance(result, EffectEnvelope)
    assert result.verification.passed is True
    assert "no postconditions" in result.verification.detail


# ---------------------------------------------------------------------------
# AUTHORIZE is fail-closed — zero effects on refusal (NAT-01 zero-effects half)
# ---------------------------------------------------------------------------

async def test_capability_outside_manifest_refused_zero_effects():
    adapter = SpyAdapter("fs.default")
    engine = _engine({"fs.default": adapter})

    result = await engine.run(
        _manifest(required=("fs.read",)),
        "fs.read",
        intended_change={"requested_capabilities": ["ADMIN"]},
        idempotency_key="k-refuse",
    )

    assert isinstance(result, EffectFailure)
    assert result.reason == "refused"
    assert result.phase == "authorize"
    assert adapter.calls == 0


async def test_contract_not_in_manifest_is_unknown_contract():
    adapter = SpyAdapter("fs.default")
    engine = _engine({"fs.default": adapter})

    result = await engine.run(
        _manifest(contract_id="fs.read"),
        "fs.write",  # registered, but not declared in this manifest
        intended_change={},
        idempotency_key="k-unknown",
    )

    assert isinstance(result, EffectFailure)
    assert result.reason == "unknown_contract"
    assert result.phase == "authorize"
    assert adapter.calls == 0


async def test_missing_runtime_adapter_is_no_provider():
    engine = _engine({})  # registry resolves fs.default, but no adapter bound

    result = await engine.run(
        _manifest(), "fs.read", intended_change={}, idempotency_key="k-noadapter"
    )

    assert isinstance(result, EffectFailure)
    assert result.reason == "no_provider"
    assert result.phase == "authorize"


async def test_unregistered_contract_is_no_provider():
    adapter = SpyAdapter("fs.default")
    engine = _engine({"fs.default": adapter})

    result = await engine.run(
        _manifest(contract_id="ghost.op", required=("ghost.op",)),
        "ghost.op",
        intended_change={},
        idempotency_key="k-ghost",
    )

    assert isinstance(result, EffectFailure)
    assert result.reason == "no_provider"
    assert adapter.calls == 0


# ---------------------------------------------------------------------------
# VERIFY — an unverified effect is not complete (§98)
# ---------------------------------------------------------------------------

async def test_failed_postconditions_are_unverified_not_complete():
    adapter = SpyAdapter("fs.default", result={"ok": False})
    engine = _engine({"fs.default": adapter})

    result = await engine.run(
        _manifest(),
        "fs.read",
        intended_change={},
        postconditions={"ok": True},
        idempotency_key="k-unverified",
    )

    assert isinstance(result, EffectFailure)
    assert result.reason == "unverified"
    assert result.phase == "verify"
    assert adapter.calls == 1


async def test_adapter_exception_maps_to_typed_adapter_error():
    adapter = SpyAdapter("fs.default", raises=RuntimeError("boom"))
    engine = _engine({"fs.default": adapter})

    result = await engine.run(
        _manifest(), "fs.read", intended_change={}, idempotency_key="k-boom"
    )

    assert isinstance(result, EffectFailure)
    assert result.reason == "adapter_error"
    assert result.phase == "commit"


# ---------------------------------------------------------------------------
# Events: one terminal event per run; exact ordering; chain integrity
# ---------------------------------------------------------------------------

async def test_success_event_order_and_chain(tmp_path):
    log = EventLog(db_path=str(tmp_path / "log.db"))
    engine = _engine({"fs.default": SpyAdapter("fs.default")}, log=log)

    result = await engine.run(
        _manifest(),
        "fs.read",
        intended_change={},
        postconditions={"ok": True},
        idempotency_key="k-order-ok",
    )

    assert isinstance(result, EffectEnvelope)
    events = log.replay()
    assert [e.event_type for e in events] == [
        "effect.prepared",
        "effect.authorized",
        "effect.committed",
        "effect.verified",
    ]
    assert all(e.stream_id == "effect" for e in events)
    assert result.audit_event_ids == [e.event_id for e in events]
    assert log.verify_chain() is True


async def test_refused_emits_only_prepared_then_refused(tmp_path):
    log = EventLog(db_path=str(tmp_path / "log.db"))
    engine = _engine({"fs.default": SpyAdapter("fs.default")}, log=log)

    result = await engine.run(
        _manifest(required=("fs.read",)),
        "fs.read",
        intended_change={"requested_capabilities": ["ADMIN"]},
        idempotency_key="k-order-refused",
    )

    assert isinstance(result, EffectFailure)
    assert [e.event_type for e in log.replay()] == [
        "effect.prepared",
        "effect.refused",
    ]
    assert log.verify_chain() is True


async def test_unverified_event_order_ends_failed(tmp_path):
    log = EventLog(db_path=str(tmp_path / "log.db"))
    engine = _engine(
        {"fs.default": SpyAdapter("fs.default", result={"ok": False})}, log=log
    )

    result = await engine.run(
        _manifest(),
        "fs.read",
        intended_change={},
        postconditions={"ok": True},
        idempotency_key="k-order-unverified",
    )

    assert isinstance(result, EffectFailure)
    assert [e.event_type for e in log.replay()] == [
        "effect.prepared",
        "effect.authorized",
        "effect.committed",
        "effect.failed",
    ]
    assert log.verify_chain() is True


async def test_committed_event_payload_carries_effect_record(tmp_path):
    log = EventLog(db_path=str(tmp_path / "log.db"))
    engine = _engine({"fs.default": SpyAdapter("fs.default")}, log=log)

    await engine.run(
        _manifest(),
        "fs.read",
        intended_change={"path": "/tmp/x"},
        idempotency_key="k-payload",
    )

    committed = next(e for e in log.replay() if e.event_type == "effect.committed")
    assert committed.payload["manifest_id"] == "manifest-1"
    assert committed.payload["contract_id"] == "fs.read"
    assert committed.payload["provider_id"] == "fs.default"
    assert committed.payload["intended_change"] == {"path": "/tmp/x"}


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

async def test_duplicate_idempotency_key_returns_prior_and_emits_nothing(tmp_path):
    log = EventLog(db_path=str(tmp_path / "log.db"))
    adapter = SpyAdapter("fs.default")
    engine = _engine({"fs.default": adapter}, log=log)
    manifest = _manifest()

    first = await engine.run(
        manifest, "fs.read", intended_change={}, idempotency_key="k-dup"
    )
    assert isinstance(first, EffectEnvelope)
    before = [e.event_type for e in log.replay()]

    second = await engine.run(
        manifest, "fs.read", intended_change={}, idempotency_key="k-dup"
    )

    assert isinstance(second, EffectEnvelope)
    assert second.duplicate is True
    assert second.effect_id == first.effect_id
    assert adapter.calls == 1
    assert [e.event_type for e in log.replay()] == before


# ---------------------------------------------------------------------------
# Seam / encapsulation
# ---------------------------------------------------------------------------

async def test_adapters_map_is_private():
    engine = _engine({"fs.default": SpyAdapter("fs.default")})

    assert not hasattr(engine, "adapters")
    assert getattr(engine, "adapters", None) is None


async def test_log_none_is_fully_in_memory():
    engine = _engine({"fs.default": SpyAdapter("fs.default")})

    assert engine._log is None  # noqa: SLF001
    result = await engine.run(
        _manifest(), "fs.read", intended_change={}, idempotency_key="k-mem"
    )

    assert isinstance(result, EffectEnvelope)
    assert result.audit_event_ids == []
