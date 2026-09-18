from __future__ import annotations

"""Freebuff/DeepSeek red-team evidence tests — module 6 review, addendum session.

These tests DOCUMENT current behavior that the review flags as defective
(assert-what-TODAY-does form, with SHOULD comments). They are review evidence,
not acceptance criteria. Do not flip them into requirements without a fix.

Attack surfaces covered:
- F7: a single provider exposing the same contract_id at two versions — the
      gateway derives contract_version by FIRST contract_id match, not by the
      version the constraint actually resolved (model_gateway.py:201-204).
- F8: a broken schema validator (raises a non-ValidationError) is mislabeled
      `validation_exhausted` as though the MODEL output were garbage, and the
      JARVIS-side bug text is fed back to the provider as "feedback".
- F9: fallback wiring is STATIC (adapter-map key) only — a primary that raises
      ProviderTransportError never triggers the declared fallback chain, so
      ADR-004/§131.4 fallback semantics are not exercised at runtime.
- F10: intent.py Manifest docstring "manifest_sha256 does NOT cover temporal
      fields" is FALSE as written — created_at_utc IS hashed (intent.py:449-451).
- F11: caret dialect is asymmetric about whitespace on the VERSION side: a
      padded registered version resolves under "^1" but never under exact "1.0.0".
"""

import json

import pytest
from pydantic import BaseModel, field_validator

import jarvis.kernel.intent as intent_mod
from jarvis.kernel.model_gateway import (
    ModelGateway,
    ProviderTransportError,
    RoleContract,
    TypedFailure,
    ValidatedOutput,
)
from jarvis.kernel.registry import (
    CapabilityRegistry,
    ContractDef,
    ProviderBinding,
    ProviderMeta,
    RegistryError,
)

pytestmark = pytest.mark.anyio


class Note(BaseModel):
    text: str
    n: int = 0


def _meta(provider_id: str, fallback: str | None = None) -> ProviderMeta:
    return ProviderMeta(
        provider_id=provider_id,
        version="1.0.0",
        license="MIT",
        license_compatibility="approved",
        adapter="jarvis.providers.test",
        trust_level="trusted",
        process_model="in_process",
        network="none",
        health_check="probe",
        cve_status="checked_clean",
        provenance_added_by="creator",
        provenance_added_at_utc="2026-09-16T00:00:00Z",
        provenance_reason="red-team review fixture",
        fallback_provider_id=fallback,
    )


def _contract(contract_id: str, version: str, schema=None) -> ContractDef:
    return ContractDef(
        contract_id=contract_id,
        version=version,
        args_schema=schema or {"x": {"type": "string", "required": True}},
    )


def _binding(provider_id: str, contracts: list[ContractDef], fallback=None):
    return ProviderBinding(meta=_meta(provider_id, fallback), contracts=contracts)


# ---------------------------------------------------------------------------
# F7: contract_version = FIRST contract_id match, not the resolved version
# ---------------------------------------------------------------------------


async def test_evidence_dual_version_contract_records_wrong_version():
    """A provider may legally expose model.generate_structured at 1.0.0 AND
    2.0.0 (register_provider does not forbid duplicates). The gateway resolves
    `^2` to 2.0.0 but then re-derives contract_version as the FIRST
    contract_id match (1.0.0) and hands THAT to the adapter — so
    ValidatedOutput.contract_version and the adapter's version arg both lie."""
    registry = CapabilityRegistry()
    registry.register_provider(
        "creator",
        _binding(
            "model.dual",
            [
                _contract("model.generate_structured", "1.0.0"),
                _contract("model.generate_structured", "2.0.0"),
            ],
        ),
    )

    assert registry.resolve_version("model.generate_structured", "^2") == "2.0.0"

    class CaptureAdapter:
        provider_id = "model.dual"

        def __init__(self):
            self.version_seen = None

        async def invoke(self, contract_id, version, args):
            self.version_seen = version
            return {"text": "ok", "n": 1}

        def health_check(self):
            return True

    adapter = CaptureAdapter()
    gateway = ModelGateway(resolver=registry, adapters={"model.dual": adapter})

    result = await gateway.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Note)

    assert isinstance(result, ValidatedOutput)
    assert result.contract_version == "1.0.0"  # evidence: SHOULD be "2.0.0"
    assert adapter.version_seen == "1.0.0"  # evidence: SHOULD be "2.0.0"


# ---------------------------------------------------------------------------
# F8: non-ValidationError from the schema validator -> mislabeled as model garbage
# ---------------------------------------------------------------------------


class BrokenSchema(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def _boom(cls, v):  # JARVIS-side bug, not a model defect
        raise RuntimeError("kernel bug in validator")


class EchoAdapter:
    provider_id = "model.adapter"

    def __init__(self):
        self.seen_feedback = []

    async def invoke(self, contract_id, version, args):
        self.seen_feedback.append(list(args.get("feedback") or []))
        return {"text": "well-formed"}  # model output is fine; schema is broken

    def health_check(self):
        return True


async def test_evidence_schema_bug_reported_as_validation_exhausted():
    """model_validate raising a NON-ValidationError (here RuntimeError) is
    caught by the same `except Exception` (model_gateway.py:249) as output
    validation, appended to feedback, and retried to exhaustion — the caller
    sees reason='validation_exhausted' with a detail blaming model output,
    never adapter_error/bug. The JARVIS-side error text is also sent to the
    model in the next prompt (feedback leak of kernel internals)."""
    registry = CapabilityRegistry.seed_m1_defaults()
    adapter = EchoAdapter()
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": adapter})

    result = await gateway.generate_structured(RoleContract.SCHEMA_CONSTRAINED, BrokenSchema)

    assert isinstance(result, TypedFailure)
    assert result.reason == "validation_exhausted"  # evidence: kernel bug mislabeled
    assert adapter.seen_feedback[-1][0].startswith("RuntimeError: kernel bug in validator")


# ---------------------------------------------------------------------------
# F9: fallback is static-key only — a live transport failure never falls back
# ---------------------------------------------------------------------------


async def test_evidence_no_runtime_failover_on_transport_error():
    """Providing a fallback adapter in the map only matters when the primary is
    MISSING from the map (_select_adapter). If the primary adapter is bound but
    raises ProviderTransportError, the gateway returns transport_error with
    attempts=1 and never touches the declared fallback (model_gateway.py:234).
    So §131.4's fallback chain and §131.11's 'failover semantics' are static
    configuration, not runtime behavior."""
    registry = CapabilityRegistry()
    registry.register_provider(
        "creator",
        _binding(
            "model.primary",
            [_contract("model.generate_structured", "1.0.0")],
            fallback="model.backup",
        ),
    )

    class BoomPrimary:
        provider_id = "model.primary"

        async def invoke(self, contract_id, version, args):
            raise ProviderTransportError("primary down")

        def health_check(self):
            return False

    class Backup:
        provider_id = "model.backup"
        calls = 0

        async def invoke(self, contract_id, version, args):
            type(self).calls += 1
            return {"text": "recovered"}

        def health_check(self):
            return True

    gateway = ModelGateway(
        resolver=registry,
        adapters={"model.primary": BoomPrimary(), "model.backup": Backup()},
    )

    result = await gateway.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Note)

    assert isinstance(result, TypedFailure)
    assert result.reason == "transport_error"
    assert Backup.calls == 0  # evidence: declared fallback chain never engaged


# ---------------------------------------------------------------------------
# F10: manifest_sha256 DOES cover created_at_utc — Manifest docstring is false
# ---------------------------------------------------------------------------


class _FixedClock:
    def __init__(self, iso: str):
        self._iso = iso

    def now_utc_iso(self) -> str:
        return self._iso


def test_evidence_manifest_hash_covers_created_at_utc(monkeypatch):
    """intent.py:185-187 (Manifest docstring) claims manifest_sha256 does NOT
    cover created_at_utc. The code hashes body_dict that includes it
    (intent.py:441-451). Two otherwise identical proposals produced at
    different clock times yield different manifest_sha256 -> coverage proven.
    Also contradicts module docstring #6 (intent.py:41-46) which says the
    opposite. The docstring lies about what the verified code does."""
    from jarvis.kernel.intent import ContractProposal, ContractSeed

    def make_proposal():
        return ContractProposal(
            contracts=[
                ContractSeed(
                    id="fs.read", version_constraint="^1.0", args={"path": "/tmp/x"}
                )
            ],
            intent_id="fixed-intent-ulid",
        )

    registry = CapabilityRegistry.seed_m1_defaults()

    monkeypatch.setattr(intent_mod, "new_ulid", lambda *a, **k: "fixed-manifest-ulid")
    monkeypatch.setattr(
        intent_mod, "_clock", _FixedClock("2026-09-17T00:00:00.000Z")
    )
    m1 = intent_mod.validate_proposal(make_proposal(), registry, [])

    monkeypatch.setattr(
        intent_mod, "_clock", _FixedClock("2026-09-18T00:00:00.000Z")
    )
    m2 = intent_mod.validate_proposal(make_proposal(), registry, [])

    assert m1.manifest_sha256 != m2.manifest_sha256  # hash MOVES with created_at

    # Re-confirm nothing else in the body changed:
    d1, d2 = m1.model_dump(), m2.model_dump()
    for k in d1:
        if k not in ("created_at_utc", "manifest_sha256"):
            assert d1[k] == d2[k], f"{k} unexpectedly differed"


# ---------------------------------------------------------------------------
# F11: caret exact-vs-caret asymmetry on whitespace-padded registered version
# ---------------------------------------------------------------------------


def test_evidence_whitespace_version_ok_under_caret_not_exact():
    """register_provider does not validate the version string. A registered
    version '1.0.0 ' (trailing space) quietly becomes: invisible to exact
    constraint '1.0.0', resolvable under '^1', and the padded string leaks
    into ResolvedContract.version / ValidatedOutput.contract_version.
    Same contract, two contradictory resolution answers depending on dialect."""
    registry = CapabilityRegistry()
    registry.register_provider(
        "creator",
        _binding("prov.pad", [_contract("c.p", "1.0.0 ")]),
    )

    assert registry.has_contract("c.p", "1.0.0") is False  # exact misses padded
    assert registry.has_contract("c.p", "^1") is True  # caret ignores padding
    assert registry.resolve_version("c.p", "^1") == "1.0.0 "  # padded leaks out


# ---------------------------------------------------------------------------
# Positive invariants (held; part of the no-findings list)
# ---------------------------------------------------------------------------


def test_registry_rejects_empty_args_schema():
    """intent.py:63-67 'registry invariant' paragraph is TRUE of the code: the
    only mutation path (register_provider) raises RegistryError on an empty
    args_schema, so get_args_schema never needs its {} fallback in practice."""
    registry = CapabilityRegistry()
    with pytest.raises(RegistryError):
        registry.register_provider(
            "creator",
            _binding(
                "prov.empty",
                [ContractDef(contract_id="c.e", version="1.0.0", args_schema={})],
            ),
        )


def test_get_args_schema_is_total():
    registry = CapabilityRegistry()
    assert isinstance(registry.get_args_schema("nope", "1.0.0"), dict)
    assert registry.get_args_schema("nope", "1.0.0") == {}

    registry = CapabilityRegistry.seed_m1_defaults()
    as_dict = registry.get_args_schema("fs.read", "1.0.0")
    assert isinstance(as_dict, dict) and as_dict
    assert "path" in as_dict