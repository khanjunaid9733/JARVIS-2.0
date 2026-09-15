from __future__ import annotations

"""Tests for intent ABI and deterministic static validation (module 3)."""

from typing import Any

import pytest

from jarvis.kernel.intent import (
    Budget,
    ContractProposal,
    ContractSeed,
    Intent,
    Manifest,
    ResolvedContract,
    RiskClass,
    ValidationFailure,
    validate_proposal,
)


# ---------------------------------------------------------------------------
# Helpers — FakeCatalog
# ---------------------------------------------------------------------------


class FakeCatalog:
    """Minimal ContractCatalog implementation for tests.

    Contracts dict: {id: {version_constraint: resolved_version}}.
    Schemas dict:   {(id, resolved_version): {field: descriptor}}.
    """

    def __init__(
        self,
        *,
        contracts: dict[str, dict[str, str]] | None = None,
        schemas: dict[tuple[str, str], dict[str, Any]] | None = None,
    ) -> None:
        self._contracts = contracts or {}
        self._schemas = schemas or {}

    def has_contract(self, contract_id: str, version_constraint: str) -> bool:
        return contract_id in self._contracts

    def resolve_version(self, contract_id: str, version_constraint: str) -> str | None:
        return self._contracts.get(contract_id, {}).get(version_constraint)

    def get_args_schema(self, contract_id: str, resolved_version: str) -> dict[str, Any]:
        return self._schemas.get((contract_id, resolved_version), {})


def _make_catalog(
    *,
    contracts: dict[str, str] | None = None,
    schemas: dict[str, dict[str, Any]] | None = None,
) -> FakeCatalog:
    """Quick helper: contracts = {id: resolved_version}, schemas = {id: schema}.
    Maps version_constraint="^1.0" (matching what tests/proposals use) to the
    given resolved_version."""
    c: dict[str, dict[str, str]] = {}
    s: dict[tuple[str, str], dict[str, Any]] = {}
    for cid, ver in (contracts or {}).items():
        c[cid] = {"^1.0": ver}
    for cid, schema in (schemas or {}).items():
        if cid in c:
            for resolved in c[cid].values():
                s[(cid, resolved)] = schema
    return FakeCatalog(contracts=c, schemas=s)


# ---------------------------------------------------------------------------
# Schema unit tests
# ---------------------------------------------------------------------------


class TestIntentSchema:
    def test_intent_roundtrip(self):
        i = Intent(
            intent_id="01HXYZ12345678901234567890",
            principal_id="user-1",
            objective="read a file",
            domain="filesystem",
        )
        assert i.intent_id == "01HXYZ12345678901234567890"
        assert i.principal_id == "user-1"
        assert i.risk_class == "safe"
        assert i.subject_refs == []
        assert i.constraints == {}

    def test_intent_extra_fields_forbidden(self):
        with pytest.raises(Exception):  # ValidationError
            Intent(
                intent_id="X",
                principal_id="u",
                objective="o",
                domain="d",
                bogus=42,  # type: ignore[call-arg]
            )

    def test_intent_risk_class_literal(self):
        i = Intent(
            intent_id="X",
            principal_id="u",
            objective="o",
            domain="d",
            risk_class="high",
        )
        assert i.risk_class == "high"

    def test_intent_invalid_risk_class_rejected(self):
        with pytest.raises(Exception):
            Intent(
                intent_id="X",
                principal_id="u",
                objective="o",
                domain="d",
                risk_class="ultra",  # type: ignore[call-arg]
            )


class TestContractProposalSchema:
    def test_proposal_defaults(self):
        p = ContractProposal()
        assert p.contracts == []
        assert p.required_capabilities == []
        assert p.intent_id is None
        assert p.risk_class == "safe"
        assert p.budget.tokens is None

    def test_proposal_with_contracts(self):
        p = ContractProposal(
            contracts=[
                ContractSeed(id="fs.read", version_constraint="^1.0", args={"path": "/x"}),
            ],
            required_capabilities=["READ_FS"],
            intent_id="some-intent",
        )
        assert len(p.contracts) == 1
        assert p.contracts[0].id == "fs.read"
        assert p.intent_id == "some-intent"


class TestBudgetSchema:
    def test_budget_defaults(self):
        b = Budget()
        assert b.tokens is None
        assert b.wall_seconds is None
        assert b.usd is None

    def test_budget_extra_forbidden(self):
        with pytest.raises(Exception):
            Budget(tokens=100, bogus="x")  # type: ignore[call-arg]


class TestManifestSchema:
    def test_manifest_is_frozen(self):
        m = Manifest(
            manifest_id="M1",
            intent_id="I1",
            contracts=[],
            required_capabilities=[],
            budget=Budget(),
            constraints={},
            risk_class="safe",
            manifest_sha256="abc",
            created_at_utc="2026-01-01T00:00:00Z",
        )
        with pytest.raises(Exception):  # ValidationError or AttributeError
            m.manifest_id = "M2"  # type: ignore[misc]


class TestResolvedContract:
    def test_resolved_contract_roundtrip(self):
        rc = ResolvedContract(id="fs.read", version="1.0.0", args={"path": "/x"})
        assert rc.version == "1.0.0"


# ---------------------------------------------------------------------------
# validate_proposal — success path
# ---------------------------------------------------------------------------


class TestValidateProposalSuccess:
    def test_basic_success(self):
        catalog = _make_catalog(contracts={"fs.read": "1.0.0"})
        proposal = ContractProposal(
            contracts=[
                ContractSeed(id="fs.read", version_constraint="^1.0", args={"path": "/project"}),
            ],
            required_capabilities=["READ_FS"],
            intent_id="intent-1",
        )
        result = validate_proposal(proposal, catalog, ["READ_FS"])
        assert isinstance(result, Manifest)
        assert result.intent_id == "intent-1"
        assert result.contracts[0].id == "fs.read"
        assert result.contracts[0].version == "1.0.0"
        assert len(result.manifest_sha256) == 64

    def test_empty_proposal_passes(self):
        catalog = _make_catalog()
        proposal = ContractProposal(contracts=[], intent_id="empty")
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, Manifest)
        assert result.contracts == []

    def test_manifest_sha256_matches_canonical_body(self):
        from jarvis.kernel.event_log import _canonical_json
        import hashlib
        catalog = _make_catalog(contracts={"fs.read": "1.0.0"})
        proposal = ContractProposal(
            contracts=[
                ContractSeed(id="fs.read", version_constraint="^1.0", args={"path": "/x"}),
            ],
            required_capabilities=["READ_FS"],
            intent_id="sha-test",
            budget=Budget(tokens=1000),
        )
        manifest = validate_proposal(proposal, catalog, ["READ_FS"])
        assert isinstance(manifest, Manifest)
        body = {
            "manifest_id": manifest.manifest_id,
            "intent_id": manifest.intent_id,
            "contracts": [rc.model_dump() for rc in manifest.contracts],
            "required_capabilities": manifest.required_capabilities,
            "budget": manifest.budget.model_dump(),
            "constraints": manifest.constraints,
            "risk_class": manifest.risk_class,
            "created_at_utc": manifest.created_at_utc,
        }
        expected_sha = hashlib.sha256(_canonical_json(body)).hexdigest()
        assert manifest.manifest_sha256 == expected_sha

    def test_intent_id_fallback_when_none(self):
        catalog = _make_catalog(contracts={"git.status": "1.0.0"})
        proposal = ContractProposal(
            contracts=[
                ContractSeed(id="git.status", version_constraint="^1.0", args={}),
            ],
            required_capabilities=[],
            intent_id=None,
        )
        manifest = validate_proposal(proposal, catalog, [])
        assert isinstance(manifest, Manifest)
        assert len(manifest.intent_id) == 26  # ULID


# ---------------------------------------------------------------------------
# validate_proposal — check 1: unknown contract
# ---------------------------------------------------------------------------


class TestCheck1UnknownContract:
    def test_unknown_contract(self):
        catalog = _make_catalog()
        proposal = ContractProposal(
            contracts=[
                ContractSeed(id="nonexistent", version_constraint="^1.0", args={}),
            ],
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, ValidationFailure)
        assert result.reason == "unknown_contract"
        assert result.contract_id == "nonexistent"


# ---------------------------------------------------------------------------
# validate_proposal — check 2: unresolvable version
# ---------------------------------------------------------------------------


class TestCheck2UnresolvableVersion:
    def test_unresolvable_version(self):
        catalog = _make_catalog(contracts={"fs.read": "2.0.0"})
        proposal = ContractProposal(
            contracts=[
                ContractSeed(id="fs.read", version_constraint="^3.0", args={}),
            ],
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, ValidationFailure)
        assert result.reason == "unresolvable_version"
        assert result.contract_id == "fs.read"


# ---------------------------------------------------------------------------
# validate_proposal — check 3: invalid args
# ---------------------------------------------------------------------------


class TestCheck3InvalidArgs:
    def test_extra_field_rejected(self):
        catalog = _make_catalog(
            contracts={"fs.read": "1.0.0"},
            schemas={"fs.read": {"path": {"type": "string"}}},
        )
        proposal = ContractProposal(
            contracts=[
                ContractSeed(
                    id="fs.read",
                    version_constraint="^1.0",
                    args={"path": "/x", "extra_field": "bad"},
                ),
            ],
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, ValidationFailure)
        assert result.reason == "invalid_args"

    def test_missing_required_field(self):
        catalog = _make_catalog(
            contracts={"fs.read": "1.0.0"},
            schemas={"fs.read": {"path": {"type": "string", "required": True}}},
        )
        proposal = ContractProposal(
            contracts=[
                ContractSeed(id="fs.read", version_constraint="^1.0", args={}),
            ],
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, ValidationFailure)
        assert result.reason == "invalid_args"
        assert "required field missing" in result.detail

    def test_wrong_type_rejected(self):
        catalog = _make_catalog(
            contracts={"fs.read": "1.0.0"},
            schemas={"fs.read": {"path": {"type": "string"}}},
        )
        proposal = ContractProposal(
            contracts=[
                ContractSeed(
                    id="fs.read",
                    version_constraint="^1.0",
                    args={"path": 123},  # int, not string
                ),
            ],
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, ValidationFailure)
        assert result.reason == "invalid_args"
        assert "expected type 'string'" in result.detail

    def test_enum_violation(self):
        catalog = _make_catalog(
            contracts={"mode.select": "1.0.0"},
            schemas={
                "mode.select": {
                    "mode": {"type": "string", "enum": ["read", "write"]},
                }
            },
        )
        proposal = ContractProposal(
            contracts=[
                ContractSeed(
                    id="mode.select",
                    version_constraint="^1.0",
                    args={"mode": "execute"},  # not in enum
                ),
            ],
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, ValidationFailure)
        assert result.reason == "invalid_args"
        assert "enum" in result.detail

    def test_no_schema_means_any_args_accepted(self):
        """When a catalog omits an args schema for a contract, any args
        pass through without validation (no schema = no constraints)."""
        catalog = _make_catalog(contracts={"noop": "1.0.0"})
        proposal = ContractProposal(
            contracts=[
                ContractSeed(
                    id="noop",
                    version_constraint="^1.0",
                    args={"anything": "goes"},
                ),
            ],
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, Manifest)


# ---------------------------------------------------------------------------
# validate_proposal — check 4: dependency cycle
# ---------------------------------------------------------------------------


class TestCheck4Dag:
    def test_no_cycle_with_args_cross_ref(self):
        """A → B via args, no cycle."""
        catalog = _make_catalog(contracts={"A": "1.0.0", "B": "1.0.0"})
        proposal = ContractProposal(
            contracts=[
                ContractSeed(id="A", version_constraint="^1.0", args={"needs": "B"}),
                ContractSeed(id="B", version_constraint="^1.0", args={}),
            ],
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, Manifest)

    def test_cycle_detected(self):
        """A → B → A cycle."""
        catalog = _make_catalog(contracts={"A": "1.0.0", "B": "1.0.0"})
        proposal = ContractProposal(
            contracts=[
                ContractSeed(id="A", version_constraint="^1.0", args={"needs": "B"}),
                ContractSeed(id="B", version_constraint="^1.0", args={"needs": "A"}),
            ],
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, ValidationFailure)
        assert result.reason == "dependency_cycle"

    def test_cycle_via_list_element(self):
        """A → [B], B → A cycle."""
        catalog = _make_catalog(contracts={"A": "1.0.0", "B": "1.0.0"})
        proposal = ContractProposal(
            contracts=[
                ContractSeed(id="A", version_constraint="^1.0", args={"deps": ["B"]}),
                ContractSeed(id="B", version_constraint="^1.0", args={"deps": ["A"]}),
            ],
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, ValidationFailure)
        assert result.reason == "dependency_cycle"

    def test_self_ref_ignored(self):
        """A self-references A — not a real cycle."""
        catalog = _make_catalog(contracts={"A": "1.0.0"})
        proposal = ContractProposal(
            contracts=[
                ContractSeed(id="A", version_constraint="^1.0", args={"self": "A"}),
            ],
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, Manifest)


# ---------------------------------------------------------------------------
# validate_proposal — check 5: ungranted capability (NAT-01)
# ---------------------------------------------------------------------------


class TestCheck5CapabilitySubset:
    def test_granted_sufficient(self):
        catalog = _make_catalog(contracts={"fs.read": "1.0.0"})
        proposal = ContractProposal(
            contracts=[
                ContractSeed(id="fs.read", version_constraint="^1.0", args={}),
            ],
            required_capabilities=["READ_FS", "LIST_DIR"],
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, ["READ_FS", "LIST_DIR", "EXEC"])
        assert isinstance(result, Manifest)

    def test_granted_as_set(self):
        """granted_capabilities may be a set, not just a list."""
        catalog = _make_catalog(contracts={"fs.read": "1.0.0"})
        proposal = ContractProposal(
            contracts=[
                ContractSeed(id="fs.read", version_constraint="^1.0", args={}),
            ],
            required_capabilities=["READ_FS"],
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, {"READ_FS"})
        assert isinstance(result, Manifest)


# ---------------------------------------------------------------------------
# NAT-01 — deterministic half
# ---------------------------------------------------------------------------


class TestNAT01:
    def test_nat_01_proposal_with_ungranted_capability_is_rejected(self):
        """NAT-01 (spec §134.3): a proposal requiring a capability that is
        not granted must be rejected as ValidationFailure with no Manifest.

        This is the deterministic half of NAT-01. The 'zero effects
        executed' half becomes testable when the effects module lands."""
        catalog = _make_catalog(contracts={"fs.read": "1.0.0"})
        proposal = ContractProposal(
            contracts=[
                ContractSeed(
                    id="fs.read",
                    version_constraint="^1.0",
                    args={"path": "/secret"},
                ),
            ],
            required_capabilities=["ADMIN"],  # not in granted set
            intent_id="nat-01-test",
        )
        result = validate_proposal(proposal, catalog, ["READ_FS"])
        assert isinstance(result, ValidationFailure)
        assert result.reason == "ungranted_capability"
        assert result.contract_id is None
        assert "ADMIN" in result.detail
        # Confirm: no Manifest produced
        assert not isinstance(result, Manifest)


# ---------------------------------------------------------------------------
# Integration / edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_multiple_failures_report_first(self):
        """Check order matters: unknown contract is reported before capability
        subset even when both conditions are violated."""
        catalog = _make_catalog()  # no contracts
        proposal = ContractProposal(
            contracts=[
                ContractSeed(id="ghost", version_constraint="^1.0", args={}),
            ],
            required_capabilities=["SHADOW"],
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, ValidationFailure)
        assert result.reason == "unknown_contract"  # check 1 beats check 5

    def test_constraint_passes_through_to_manifest(self):
        catalog = _make_catalog(contracts={"a": "1.0.0"})
        proposal = ContractProposal(
            contracts=[ContractSeed(id="a", version_constraint="^1.0", args={})],
            constraints={"timeout": 30},
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, Manifest)
        assert result.constraints == {"timeout": 30}

    def test_budget_passes_through_to_manifest(self):
        catalog = _make_catalog(contracts={"a": "1.0.0"})
        proposal = ContractProposal(
            contracts=[ContractSeed(id="a", version_constraint="^1.0", args={})],
            budget=Budget(tokens=5000, wall_seconds=60),
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, Manifest)
        assert result.budget.tokens == 5000
        assert result.budget.wall_seconds == 60

    def test_risk_class_passes_through(self):
        catalog = _make_catalog(contracts={"a": "1.0.0"})
        proposal = ContractProposal(
            contracts=[ContractSeed(id="a", version_constraint="^1.0", args={})],
            risk_class="critical",
            intent_id="i1",
        )
        result = validate_proposal(proposal, catalog, [])
        assert isinstance(result, Manifest)
        assert result.risk_class == "critical"

    def test_invalid_risk_class_rejected_by_pydantic(self):
        """Proposal with invalid risk_class is rejected at schema level."""
        with pytest.raises(Exception):
            ContractProposal(
                contracts=[ContractSeed(id="a", version_constraint="^1.0")],
                risk_class="ultra",  # type: ignore[call-arg]
                intent_id="i1",
            )
