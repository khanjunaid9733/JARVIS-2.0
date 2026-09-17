from __future__ import annotations

"""Module 6 gateway tests (ADR-006). No live network; doubly-fake adapters."""

import pytest
from pydantic import BaseModel

from jarvis.kernel.model_gateway import (
    M1_ROLE_CONTRACTS,
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
)

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeModelAdapter:
    """Scriptable ProviderAdapter. Outputs are drained in order on invoke."""

    provider_id = "model.adapter"

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.invoked_args = []
        self.invoked_versions = []
        self.calls = 0

    async def invoke(self, contract_id, version, args):
        self.calls += 1
        self.invoked_args.append(args)
        self.invoked_versions.append(version)
        if not self.outputs:
            return {}
        return self.outputs.pop(0)

    def health_check(self):
        return True


class SpyAdapter:
    """Adapter that must never be invoked (fs/terminal/http spies)."""

    def __init__(self, provider_id):
        self._provider_id = provider_id
        self.calls = 0

    @property
    def provider_id(self):
        return self._provider_id

    async def invoke(self, contract_id, version, args):
        self.calls += 1
        return {}

    def health_check(self):
        return True


class FailingAdapter:
    provider_id = "model.adapter"

    async def invoke(self, contract_id, version, args):
        raise ProviderTransportError(f"boom on {contract_id}")

    def health_check(self):
        return False


class Note(BaseModel):
    text: str
    n: int = 0


# ---------------------------------------------------------------------------
# Resolution through a seeded registry
# ---------------------------------------------------------------------------

def test_resolves_through_seeded_registry():
    registry = CapabilityRegistry.seed_m1_defaults()
    assert registry.resolve_provider("model.generate_structured", "^1.0") == "model.adapter"


async def test_generate_structured_valid_output():
    registry = CapabilityRegistry.seed_m1_defaults()
    fake = FakeModelAdapter([{"text": "hello", "n": 1}])
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": fake})

    result = await gateway.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Note)

    assert isinstance(result, ValidatedOutput)
    assert result.value.text == "hello"
    assert result.value.n == 1
    assert result.role_contract == RoleContract.SCHEMA_CONSTRAINED
    assert result.provider_id == "model.adapter"
    assert result.attempts == 1
    assert result.contract_id == "model.generate_structured"
    assert result.contract_version == "1.0.0"


# ---------------------------------------------------------------------------
# Retry on validation failure (ADR-006 self-correction)
# ---------------------------------------------------------------------------

async def test_retries_on_validation_error_and_succeeds():
    registry = CapabilityRegistry.seed_m1_defaults()
    fake = FakeModelAdapter([{"wrong": "field"}, {"text": "ok", "n": 2}])
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": fake})

    result = await gateway.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Note)

    assert isinstance(result, ValidatedOutput)
    assert result.attempts == 2
    assert result.value.text == "ok"
    # feedback must have been attached to the second request (self-correction)
    assert fake.invoked_args[0]["feedback"] == []
    assert len(fake.invoked_args[1]["feedback"]) == 1


async def test_exhausts_retries_validation_exhausted():
    registry = CapabilityRegistry.seed_m1_defaults()
    fake = FakeModelAdapter([{"bad": 1}, {"bad": 2}, {"bad": 3}])
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": fake})

    result = await gateway.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Note)

    assert isinstance(result, TypedFailure)
    assert result.reason == "validation_exhausted"
    assert result.attempts == 3


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------

async def test_no_provider_empty_catalog():
    empty = CapabilityRegistry()
    gateway = ModelGateway(resolver=empty, adapters={})

    result = await gateway.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Note)

    assert isinstance(result, TypedFailure)
    assert result.reason == "no_provider"


async def test_transport_error_mapped_typed():
    registry = CapabilityRegistry.seed_m1_defaults()
    gateway = ModelGateway(
        resolver=registry, adapters={"model.adapter": FailingAdapter()}
    )

    result = await gateway.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Note)

    assert isinstance(result, TypedFailure)
    assert result.reason == "transport_error"
    assert "boom" in result.detail
    assert result.attempts == 1


async def test_unsupported_contract_for_declared_unbound_role():
    registry = CapabilityRegistry.seed_m1_defaults()
    gateway = ModelGateway(resolver=registry, adapters={})

    result = await gateway.generate_structured(RoleContract.PLAN, Note)

    assert isinstance(result, TypedFailure)
    assert result.reason == "unsupported_contract"


# ---------------------------------------------------------------------------
# Provider-agnostic dispatch + fallback
# ---------------------------------------------------------------------------

async def test_provider_agnostic_swap_two_adapters():
    registry = CapabilityRegistry.seed_m1_defaults()

    adapter_a = FakeModelAdapter([{"text": "from-A"}])
    gateway_a = ModelGateway(resolver=registry, adapters={"model.adapter": adapter_a})
    out_a = await gateway_a.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Note)

    class AdapterB:
        provider_id = "model.adapter"

        async def invoke(self, contract_id, version, args):
            return {"text": "from-B"}

        def health_check(self):
            return True

    gateway_b = ModelGateway(resolver=registry, adapters={"model.adapter": AdapterB()})
    out_b = await gateway_b.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Note)

    assert isinstance(out_a, ValidatedOutput) and out_a.value.text == "from-A"
    assert isinstance(out_b, ValidatedOutput) and out_b.value.text == "from-B"


async def test_fallback_provider_id_used_when_primary_unbound():
    registry = CapabilityRegistry()
    from jarvis.kernel.registry import (
        ContractDef,
        ProviderBinding,
        ProviderMeta,
    )

    registry.register_provider(
        "creator",
        ProviderBinding(
            meta=ProviderMeta(
                provider_id="model.primary",
                version="1.0.0",
                license="MIT",
                license_compatibility="approved",
                adapter="jarvis.providers.primary",
                trust_level="trusted",
                process_model="in_process",
                network="egress_only",
                health_check="probe",
                cve_status="checked_clean",
                provenance_added_by="creator",
                provenance_added_at_utc="2026-09-16T00:00:00Z",
                provenance_reason="fallback test",
                fallback_provider_id="model.backup",
            ),
            contracts=[
                ContractDef(
                    contract_id="model.generate_structured",
                    version="1.0.0",
                    args_schema={"role_contract": {"type": "string", "required": True}},
                )
            ],
        ),
    )

    class BackupAdapter:
        provider_id = "model.backup"

        async def invoke(self, contract_id, version, args):
            return {"text": "from-backup"}

        def health_check(self):
            return True

    gateway = ModelGateway(
        resolver=registry, adapters={"model.backup": BackupAdapter()}
    )

    result = await gateway.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Note)

    assert isinstance(result, ValidatedOutput)
    assert result.provider_id == "model.backup"
    assert result.value.text == "from-backup"


# ---------------------------------------------------------------------------
# Freebuff fixes: F1 contract_version, F4 schema defect handling
# ---------------------------------------------------------------------------


def _dual_version_binding() -> ProviderBinding:
    return ProviderBinding(
        meta=ProviderMeta(
            provider_id="model.adapter",
            version="1.0.0",
            license="MIT",
            license_compatibility="approved",
            adapter="jarvis.providers.dual",
            trust_level="trusted",
            process_model="in_process",
            network="egress_only",
            health_check="probe",
            cve_status="checked_clean",
            provenance_added_by="creator",
            provenance_added_at_utc="2026-09-16T00:00:00Z",
            provenance_reason="F1 dual-version regression",
        ),
        contracts=[
            ContractDef(
                contract_id="model.generate_structured",
                version="2.0.0",
                args_schema={
                    "role_contract": {"type": "string", "required": True}
                },
            ),
            ContractDef(
                contract_id="model.generate_structured",
                version="1.0.0",
                args_schema={
                    "role_contract": {"type": "string", "required": True}
                },
            ),
        ],
    )


async def test_contract_version_is_constraint_resolved_not_first_match():
    registry = CapabilityRegistry()
    registry.register_provider("creator", _dual_version_binding())
    fake = FakeModelAdapter([{"text": "x"}])
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": fake})

    result = await gateway.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Note)

    assert isinstance(result, ValidatedOutput)
    # First contract is 2.0.0; constraint ^1.0 must resolve to 1.0.0.
    assert result.contract_version == "1.0.0"
    assert fake.invoked_versions == ["1.0.0"]


async def test_schema_validator_defect_is_not_retried_or_shipped_as_feedback():
    from pydantic import field_validator

    class Explosive(BaseModel):
        text: str

        @field_validator("text")
        @classmethod
        def _boom(cls, v):
            raise RuntimeError("validator bug")

    registry = CapabilityRegistry.seed_m1_defaults()
    fake = FakeModelAdapter([{"text": "ok"}])
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": fake})

    result = await gateway.generate_structured(
        RoleContract.SCHEMA_CONSTRAINED, Explosive
    )

    assert isinstance(result, TypedFailure)
    assert result.reason == "schema_error"
    assert result.attempts == 1
    assert fake.calls == 1  # kernel defect, never retried
    assert fake.invoked_args[0]["feedback"] == []  # never shipped to model


# ---------------------------------------------------------------------------
# No effects / no tools: fs/terminal/http adapters never invoked
# ---------------------------------------------------------------------------

async def test_never_invokes_fs_terminal_http_adapters():
    registry = CapabilityRegistry.seed_m1_defaults()
    spies = {
        pid: SpyAdapter(pid)
        for pid in ("fs.default", "terminal.default", "http.default")
    }
    fake = FakeModelAdapter([{"text": "x"}])
    adapters = dict(spies)
    adapters["model.adapter"] = fake
    gateway = ModelGateway(resolver=registry, adapters=adapters)

    result = await gateway.generate_structured(RoleContract.SCHEMA_CONSTRAINED, Note)

    assert isinstance(result, ValidatedOutput)
    for spy in spies.values():
        assert spy.calls == 0


# ---------------------------------------------------------------------------
# Role contract set matches §131.13
# ---------------------------------------------------------------------------

def test_role_contract_set_matches_spec_131_13():
    expected = {
        "EXECUTE_REASONING",
        "PLAN",
        "CODE",
        "CLASSIFY",
        "VISION",
        "STT",
        "TTS",
        "EMBED",
        "RERANK",
        "PII_DETECT",
        "SCHEMA_CONSTRAINED",
        "ROBOTICS_PERCEPTION",
        "VLA_VLN",
        "SIMULATION_WORLD_MODEL",
        "SPECIALIST",
    }
    assert set(RoleContract.__members__) == expected


def test_m1_routes_only_schema_constrained():
    assert set(M1_ROLE_CONTRACTS) == {RoleContract.SCHEMA_CONSTRAINED}
    assert M1_ROLE_CONTRACTS[RoleContract.SCHEMA_CONSTRAINED] == (
        "model.generate_structured",
        "^1.0",
    )