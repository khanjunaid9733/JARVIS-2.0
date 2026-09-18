from __future__ import annotations

"""Module 4 tests: in-memory capability registry + ProviderAdapter Protocol.

Covers:
- ProviderAdapter Protocol interface shape (no import of implementations)
- schema strictness: ProviderMeta / ContractDef / ProviderBinding extra=forbid
- creator-only registration (NAT-02 deterministic half, ADR-003)
- args_schema invariant (RegistryError on empty schema)
- version constraint dialect: exact + caret-prefix ("^1.0")
- first-registered wins resolution
- ContractCatalog Protocol consumed by intent.validate_proposal (end-to-end)
- seed_m1_defaults: 4 seeded providers (§105.1), correct metadata
"""

import pytest

from jarvis.kernel.creator import AuthorityUnavailable
from jarvis.kernel.registry import (
    CREATOR_PRINCIPAL_ID,
    CapabilityRegistry,
    ContractDef,
    ProviderAdapter,
    ProviderBinding,
    ProviderMeta,
    RegistryError,
)


# ---------------------------------------------------------------------------
# ProviderAdapter Protocol interface
# ---------------------------------------------------------------------------

def test_provider_adapter_protocol_interface_surface():
    assert isinstance(ProviderAdapter, type)
    assert hasattr(ProviderAdapter, "invoke")
    assert hasattr(ProviderAdapter, "health_check")
    attrs = {name for name in dir(ProviderAdapter) if not name.startswith("_")}
    assert "provider_id" in attrs
    assert "invoke" in attrs
    assert "health_check" in attrs


# ---------------------------------------------------------------------------
# Schema strictness
# ---------------------------------------------------------------------------

def _factory_meta(**overrides):
    base = dict(
        provider_id="pv.endpoint",
        version="1.0.0",
        license="MIT",
        license_compatibility="approved",
        adapter="jarvis.adapters.dummy",
        trust_level="trusted",
        process_model="in_process",
        network="none",
        health_check="dummy",
        cve_status="checked_clean",
        provenance_added_by="creator",
        provenance_added_at_utc="2026-09-15T00:00:00Z",
        provenance_reason="test fixture",
    )
    base.update(overrides)
    return ProviderMeta(**base)


def _factory_binding(**overrides):
    base = dict(
        meta=_factory_meta(),
        contracts=[
            ContractDef(
                contract_id="pv.ping",
                version="1.0.0",
                args_schema={"target": {"type": "string", "required": True}},
            )
        ],
    )
    base.update(overrides)
    return ProviderBinding(**base)


def test_schemas_extra_forbid():
    with pytest.raises(Exception):
        _factory_binding(extra_key="must be rejected")


def test_contract_def_extra_forbid():
    with pytest.raises(Exception):
        ContractDef(
            contract_id="pv.ping",
            version="1.0.0",
            args_schema={},
            unexpected_field=True,
        )


# ---------------------------------------------------------------------------
# NAT-02 (deterministic half): non-creator registration is rejected
# ---------------------------------------------------------------------------

def test_nat_02_non_creator_registration_is_rejected():
    registry = CapabilityRegistry()
    binding = _factory_binding()

    with pytest.raises(AuthorityUnavailable) as exc_info:
        registry.register_provider("agent-7", binding)

    message = str(exc_info.value)
    assert "agent-7" in message
    assert registry.list_contracts() == []
    assert registry.get_provider("pv.endpoint") is None


def test_creator_registration_succeeds():
    registry = CapabilityRegistry()
    registry.register_provider(CREATOR_PRINCIPAL_ID, _factory_binding())
    assert registry.has_contract("pv.ping", "1.0.0")
    assert registry.get_provider("pv.endpoint") is not None


# ---------------------------------------------------------------------------
# args_schema invariant (Freebuff flag 1 from module-3 gate, closes fail-open)
# ---------------------------------------------------------------------------

def test_empty_args_schema_rejected():
    registry = CapabilityRegistry()
    binding = _factory_binding(
        contracts=[ContractDef(contract_id="pv.sloppy", version="1.0.0", args_schema={})]
    )
    with pytest.raises(RegistryError) as exc_info:
        registry.register_provider(CREATOR_PRINCIPAL_ID, binding)
    assert "pv.sloppy" in str(exc_info.value)
    assert "args_schema" in str(exc_info.value)


def test_provider_with_zero_contracts_rejected():
    registry = CapabilityRegistry()
    binding = _factory_binding(contracts=[])
    with pytest.raises(RegistryError):
        registry.register_provider(CREATOR_PRINCIPAL_ID, binding)


# ---------------------------------------------------------------------------
# Version constraint dialect
# ---------------------------------------------------------------------------

@pytest.fixture
def versioned_registry():
    registry = CapabilityRegistry()
    for version in ("1.0.0", "1.5.0", "2.0.0"):
        registry.register_provider(
            CREATOR_PRINCIPAL_ID,
            _factory_binding(
                meta=_factory_meta(provider_id=f"pv.{version}", version=version),
                contracts=[
                    ContractDef(
                        contract_id="pv.ping",
                        version=version,
                        args_schema={"target": {"type": "string", "required": True}},
                    )
                ],
            ),
        )
    return registry


def test_exact_match_wins(versioned_registry):
    assert versioned_registry.resolve_version("pv.ping", "1.5.0") == "1.5.0"


def test_caret_prefix_matches_minor_releases(versioned_registry):
    assert versioned_registry.resolve_version("pv.ping", "^1.0") == "1.0.0"


def test_caret_prefix_rejects_next_major(versioned_registry):
    assert versioned_registry.resolve_version("pv.ping", "^1.0") != "2.0.0"


def test_missing_constraint_returns_none(versioned_registry):
    assert versioned_registry.resolve_version("pv.ping", "9.9.9") is None
    assert versioned_registry.has_contract("pv.nope", "1.0.0") is False


def test_first_registered_wins(versioned_registry):
    assert versioned_registry.resolve_version("pv.ping", "^1") == "1.0.0"
    assert versioned_registry.resolve_version("pv.ping", "^2") == "2.0.0"


# ---------------------------------------------------------------------------
# M6 carry-over (F4/F5/F11): dialect hardening + re-registration precedence
# ---------------------------------------------------------------------------

def _dialect_registry(version: str) -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register_provider(
        CREATOR_PRINCIPAL_ID,
        _factory_binding(
            contracts=[
                ContractDef(
                    contract_id="c.dialect",
                    version=version,
                    args_schema={"x": {"type": "string", "required": True}},
                )
            ]
        ),
    )
    return registry


def test_caret_on_zero_major_is_rejected():
    registry = _dialect_registry("0.9.0")
    assert registry.has_contract("c.dialect", "^0.2") is False
    assert registry.resolve_version("c.dialect", "^0.2") is None
    assert registry.resolve_version("c.dialect", "0.9.0") == "0.9.0"  # exact pins


def test_prerelease_version_is_not_resolvable():
    registry = _dialect_registry("1.1.0-beta")
    assert registry.has_contract("c.dialect", "^1") is False
    assert registry.resolve_version("c.dialect", "1.1.0-beta") is None


def test_whitespace_padded_version_is_unresolvable_both_dialects():
    registry = _dialect_registry("1.0.0 ")
    assert registry.has_contract("c.dialect", "1.0.0") is False
    assert registry.has_contract("c.dialect", "^1") is False


def test_malformed_caret_constraint_is_rejected():
    registry = _dialect_registry("1.0.0")
    assert registry.has_contract("c.dialect", "^1.x") is False
    assert registry.has_contract("c.dialect", "^1") is True


def test_resolve_version_for_provider_is_scoped_to_that_provider():
    registry = CapabilityRegistry()
    registry.register_provider(
        CREATOR_PRINCIPAL_ID,
        _factory_binding(
            meta=_factory_meta(provider_id="prov.a"),
            contracts=[
                ContractDef(
                    contract_id="c.scoped",
                    version="1.0.0",
                    args_schema={"x": {"type": "string", "required": True}},
                )
            ],
        ),
    )
    registry.register_provider(
        CREATOR_PRINCIPAL_ID,
        _factory_binding(
            meta=_factory_meta(provider_id="prov.b"),
            contracts=[
                ContractDef(
                    contract_id="c.scoped",
                    version="1.2.0",
                    args_schema={"x": {"type": "string", "required": True}},
                )
            ],
        ),
    )
    assert registry.resolve_version("c.scoped", "^1") == "1.0.0"  # global first match
    assert registry.resolve_version_for_provider("prov.b", "c.scoped", "^1") == "1.2.0"
    assert registry.resolve_version_for_provider("prov.c", "c.scoped", "^1") is None


def test_reregistration_keeps_first_registered_precedence():
    registry = CapabilityRegistry()
    registry.register_provider(
        CREATOR_PRINCIPAL_ID,
        _factory_binding(
            meta=_factory_meta(provider_id="prov.a"),
            contracts=[
                ContractDef(
                    contract_id="c.x",
                    version="1.0.0",
                    args_schema={"x": {"type": "string", "required": True}},
                )
            ],
        ),
    )
    registry.register_provider(
        CREATOR_PRINCIPAL_ID,
        _factory_binding(
            meta=_factory_meta(provider_id="prov.b"),
            contracts=[
                ContractDef(
                    contract_id="c.x",
                    version="1.0.0",
                    args_schema={"x": {"type": "string", "required": True}},
                )
            ],
        ),
    )
    assert registry.resolve_provider("c.x", "1.0.0") == "prov.a"

    registry.register_provider(
        CREATOR_PRINCIPAL_ID,
        _factory_binding(
            meta=_factory_meta(provider_id="prov.b"),
            contracts=[
                ContractDef(
                    contract_id="c.x",
                    version="1.0.0",
                    args_schema={"y": {"type": "integer", "required": True}},
                )
            ],
        ),
    )
    assert registry.resolve_provider("c.x", "1.0.0") == "prov.a"
    assert registry.get_args_schema("c.x", "1.0.0") == {
        "x": {"type": "string", "required": True}
    }


# ---------------------------------------------------------------------------
# ContractCatalog Protocol surface (consumed by intent.validate_proposal)
# ---------------------------------------------------------------------------

def test_registry_satisfies_catalog_protocol():
    from jarvis.kernel.intent import ContractCatalog

    for method in ("has_contract", "resolve_version", "get_args_schema"):
        assert hasattr(ContractCatalog, method)
        assert hasattr(CapabilityRegistry, method)


def test_get_args_schema_returns_winner_schema():
    registry = CapabilityRegistry()
    registry.register_provider(
        CREATOR_PRINCIPAL_ID,
        _factory_binding(
            meta=_factory_meta(provider_id="pv.a"),
            contracts=[
                ContractDef(
                    contract_id="pv.ping",
                    version="1.0.0",
                    args_schema={"target": {"type": "string", "required": True}},
                )
            ],
        ),
    )
    schema = registry.get_args_schema("pv.ping", "1.0.0")
    assert schema == {"target": {"type": "string", "required": True}}


def test_get_args_schema_unknown_version_returns_empty_dict():
    registry = CapabilityRegistry()
    registry.register_provider(CREATOR_PRINCIPAL_ID, _factory_binding())
    assert registry.get_args_schema("pv.ping", "9.0.0") == {}


# ---------------------------------------------------------------------------
# Seed set (§105.1)
# ---------------------------------------------------------------------------

def test_seed_m1_defaults_registers_four_providers():
    registry = CapabilityRegistry.seed_m1_defaults()
    for provider_id in (
        "fs.default",
        "terminal.default",
        "model.adapter",
        "http.default",
    ):
        assert registry.get_provider(provider_id) is not None


def test_seed_m1_defaults_contracts():
    registry = CapabilityRegistry.seed_m1_defaults()
    contracts = dict(registry.list_contracts())
    assert contracts["fs.read"] == "1.0.0"
    assert contracts["fs.write"] == "1.0.0"
    assert contracts["terminal.execute"] == "1.0.0"
    assert contracts["model.generate_structured"] == "1.0.0"
    assert contracts["http.get"] == "1.0.0"
    assert contracts["http.post"] == "1.0.0"


def test_seed_m1_defaults_all_schemas_non_empty():
    registry = CapabilityRegistry.seed_m1_defaults()
    for contract_id, version in registry.list_contracts():
        assert registry.get_args_schema(contract_id, version)


def test_seed_m1_model_adapter_metadata():
    registry = CapabilityRegistry.seed_m1_defaults()
    binding = registry.get_provider("model.adapter")
    assert binding is not None
    meta = binding.meta
    assert meta.cve_status == "unchecked"
    assert meta.process_model == "remote"
    assert "module 6 binds the real backend" in meta.provenance_reason


# ---------------------------------------------------------------------------
# End-to-end: registry catalog consumed by intent.validate_proposal
# ---------------------------------------------------------------------------

def test_validate_proposal_end_to_end_with_seeded_registry():
    from jarvis.kernel.intent import (
        ContractProposal,
        ContractSeed,
        validate_proposal,
    )

    registry = CapabilityRegistry.seed_m1_defaults()
    proposal = ContractProposal(
        contracts=[
            ContractSeed(
                id="fs.read",
                version_constraint="^1",
                args={"path": "/tmp/note.txt"},
            )
        ],
    )
    manifest = validate_proposal(
        proposal=proposal,
        catalog=registry,
        granted_capabilities=["fs.read"],
    )
    assert manifest.contracts[0].version == "1.0.0"
    assert manifest.required_capabilities == []


def test_validate_proposal_rejects_ungranted_contract():
    from jarvis.kernel.intent import (
        ContractProposal,
        ContractSeed,
        validate_proposal,
    )

    registry = CapabilityRegistry.seed_m1_defaults()
    proposal = ContractProposal(
        contracts=[
            ContractSeed(
                id="terminal.execute",
                version_constraint="^1",
                args={"cmd": "ls"},
            )
        ],
        required_capabilities=["terminal.execute"],
    )
    failure = validate_proposal(
        proposal=proposal,
        catalog=registry,
        granted_capabilities=[],
    )
    assert failure.reason == "ungranted_capability"