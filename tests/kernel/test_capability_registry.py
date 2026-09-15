from __future__ import annotations

"""Tests for the capability registry (module 4)."""

import pytest

from jarvis.kernel.capability_registry import (
    CapabilityRegistry,
    ContractDecl,
    ProviderMetadata,
    ProviderMetadataError,
    RegistryAuthorityError,
    RegistryError,
)
from jarvis.kernel.creator import CreatorIdentity
from jarvis.kernel.event_log import Event, EventLog
from jarvis.kernel.intent import (
    ContractProposal,
    ContractSeed,
    Manifest,
    ValidationFailure,
    validate_proposal,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def creator(tmp_path):
    return CreatorIdentity.create(tmp_path / "keys")


@pytest.fixture
def log(tmp_path):
    return EventLog(db_path=tmp_path / "log.db")


def _seed(registry, log, creator, last_audit="2026-09-15T00:00:00Z"):
    return registry.seed(log, creator, last_audit=last_audit)


def _metadata(
    provider_id="test.provider",
    **overrides,
) -> ProviderMetadata:
    base = {
        "provider_id": provider_id,
        "license": "MIT",
        "license_compatibility": "approved",
        "adapter": "jarvis.adapters.test",
        "trust_level": "sandboxed",
        "process_model": "isolated_subprocess",
        "network_scope": "none",
        "cve_status": "checked",
        "last_audit": "2026-09-15T00:00:00Z",
        "health_check": "probe",
    }
    base.update(overrides)
    return ProviderMetadata(**base)


def _contract(contract_id="test.contract", version="1.0.0") -> ContractDecl:
    return ContractDecl(contract_id=contract_id, version=version)


# ---------------------------------------------------------------------------
# Seeding (spec §105.1)
# ---------------------------------------------------------------------------


class TestSeeding:
    def test_seed_registers_exactly_four_providers(self, creator, log):
        registry = CapabilityRegistry(creator)
        _seed(registry, log, creator)
        ids = [p.provider_id for p in registry.providers()]
        assert ids == ["fs.local", "http.client", "model.local", "terminal.local"]
        assert all(p.status == "active" for p in registry.providers())

    def test_seed_events_carried_in_event_log(self, creator, log):
        registry = CapabilityRegistry(creator)
        _seed(registry, log, creator)
        added = [
            e for e in log.replay() if e.event_type == "capability.provider_added"
        ]
        assert len(added) == 4

    def test_rebuild_from_log_reproduces_seed(self, creator, log):
        registry = CapabilityRegistry(creator)
        _seed(registry, log, creator)
        rebuilt = CapabilityRegistry.from_log(log, creator)
        assert [p.provider_id for p in rebuilt.providers()] == [
            p.provider_id for p in registry.providers()
        ]
        assert all(
            p.status == r.status
            for p, r in zip(rebuilt.providers(), registry.providers())
        )


# ---------------------------------------------------------------------------
# ContractCatalog interface
# ---------------------------------------------------------------------------


class TestCatalogInterface:
    @pytest.fixture
    def seeded(self, creator, log):
        registry = CapabilityRegistry(creator)
        _seed(registry, log, creator)
        return registry

    def test_has_contract_true_after_seed(self, seeded):
        assert seeded.has_contract("fs.read", "^1.0") is True

    def test_has_contract_false_for_unknown(self, seeded):
        assert seeded.has_contract("browser.navigate", "^1.0") is False

    def test_resolve_version_wildcard(self, seeded):
        assert seeded.resolve_version("fs.read", "*") == "1.0.0"

    def test_resolve_version_exact(self, seeded):
        assert seeded.resolve_version("fs.read", "1.0.0") == "1.0.0"

    def test_resolve_version_mismatch(self, seeded):
        assert seeded.resolve_version("fs.read", "2.0.0") is None

    def test_resolve_version_caret(self, seeded):
        assert seeded.resolve_version("model.generate_structured", "^1.0") == "1.0.0"

    def test_args_schema_exposed(self, seeded):
        schema = seeded.get_args_schema("fs.write", "1.0.0")
        assert schema["path"]["required"] is True
        assert schema["content"]["required"] is True

    def test_args_schema_unknown_contract(self, seeded):
        assert seeded.get_args_schema("ghost.contract", "1.0.0") == {}

    def test_providers_no_agent_registered(self, seeded):
        """§127.1: registry reflects exactly the seeded providers."""
        assert len(seeded.providers()) == 4


# ---------------------------------------------------------------------------
# Version resolution (decision #6)
# ---------------------------------------------------------------------------


class TestVersionResolution:
    def test_highest_wins_among_multiple(self, creator, log):
        """^1 (major-only caret) permits minor updates and picks the highest."""
        registry = CapabilityRegistry(creator)
        for version in ("1.0.0", "1.2.0"):
            registry.add(
                log,
                creator,
                _metadata(provider_id=f"prov-{version}"),
                [_contract("multi.test", version=version)],
            )
        assert registry.resolve_version("multi.test", "^1") == "1.2.0"

    def test_caret_with_minor_keeps_same_minor(self, creator, log):
        """^1.0 constrains the minor: 1.2.0 does NOT satisfy ^1.0."""
        registry = CapabilityRegistry(creator)
        registry.add(
            log,
            creator,
            _metadata(provider_id="p-1"),
            [_contract("min.test", version="1.0.0")],
        )
        registry.add(
            log,
            creator,
            _metadata(provider_id="p-2"),
            [_contract("min.test", version="1.2.0")],
        )
        assert registry.resolve_version("min.test", "^1.0") == "1.0.0"

    def test_caret_matches_major_only_without_minor(self, creator, log):
        registry = CapabilityRegistry(creator)
        registry.add(
            log,
            creator,
            _metadata(provider_id="p-a"),
            [_contract("ver.test", version="1.0.0")],
        )
        registry.add(
            log,
            creator,
            _metadata(provider_id="p-b"),
            [_contract("ver.test", version="2.0.0")],
        )
        assert registry.resolve_version("ver.test", "^1") == "1.0.0"
        assert registry.resolve_version("ver.test", "2.0.0") == "2.0.0"


# ---------------------------------------------------------------------------
# Supply-chain metadata gate (spec §131.4)
# ---------------------------------------------------------------------------


class TestMetadataGate:
    def test_add_rejects_incomplete_metadata(self, creator, log):
        registry = CapabilityRegistry(creator)
        with pytest.raises(ProviderMetadataError):
            registry.add(
                log,
                creator,
                _metadata(license=""),  # missing required license
                [_contract()],
            )

    def test_add_accepts_complete_metadata(self, creator, log):
        registry = CapabilityRegistry(creator)
        registry.add(log, creator, _metadata(), [_contract()])
        assert registry.has_contract("test.contract", "^1.0")


# ---------------------------------------------------------------------------
# Two-step ceremony (spec §105.2)
# ---------------------------------------------------------------------------


class TestTwoStepCeremony:
    def test_proposed_provider_not_usable(self, creator, log):
        registry = CapabilityRegistry(creator)
        registry.propose(
            log,
            principal_id="agent-7",
            metadata=_metadata(provider_id="agent.tool"),
            contracts=[_contract("agent.tool.call")],
        )
        assert registry.has_contract("agent.tool.call", "^1.0") is False
        assert [p.provider_id for p in registry.proposed_providers()] == [
            "agent.tool"
        ]
        assert registry.provider("agent.tool") is None

    def test_propose_then_add_activates(self, creator, log):
        registry = CapabilityRegistry(creator)
        registry.propose(
            log,
            principal_id="agent-7",
            metadata=_metadata(provider_id="agent.tool"),
            contracts=[_contract("agent.tool.call")],
        )
        registry.add(
            log,
            creator,
            _metadata(provider_id="agent.tool"),
            [ContractDecl(contract_id="agent.tool.call", version="1.0.0")],
        )
        assert registry.has_contract("agent.tool.call", "^1.0") is True
        assert registry.provider("agent.tool").status == "active"
        assert (
            registry.provider("agent.tool").registration.proposed_by == "agent-7"
        )

    def test_proposed_without_add_never_projected_as_provider(self, creator, log):
        registry = CapabilityRegistry(creator)
        registry.propose(
            log,
            principal_id="agent-7",
            metadata=_metadata(provider_id="agent.tool"),
            contracts=[_contract("agent.tool.call")],
        )
        rebuilt = CapabilityRegistry.from_log(log, creator)
        assert rebuilt.has_contract("agent.tool.call", "^1.0") is False
        assert len(rebuilt.providers()) == 0


# ---------------------------------------------------------------------------
# deprecate / revoke (spec §131.5, ADR-003)
# ---------------------------------------------------------------------------


class TestLifecycleTransitions:
    def test_revoked_provider_cannot_receive_new_work(self, creator, log):
        registry = CapabilityRegistry(creator)
        registry.add(
            log,
            creator,
            _metadata(provider_id="v.provider", repo="https://x"),
            [_contract("v.contract")],
        )
        assert registry.resolve_version("v.contract", "^1.0") == "1.0.0"
        registry.revoke(log, creator, "v.provider")
        assert registry.resolve_version("v.contract", "^1.0") is None
        assert registry.has_contract("v.contract", "^1.0") is False

    def test_revoked_survives_replay(self, creator, log):
        registry = CapabilityRegistry(creator)
        registry.add(
            log,
            creator,
            _metadata(provider_id="v.provider", repo="https://x"),
            [_contract("v.contract")],
        )
        registry.revoke(log, creator, "v.provider")
        rebuilt = CapabilityRegistry.from_log(log, creator)
        assert rebuilt.provider("v.provider").status == "revoked"
        assert rebuilt.has_contract("v.contract", "^1.0") is False

    def test_deprecated_stays_resolveable(self, creator, log):
        registry = CapabilityRegistry(creator)
        registry.add(
            log,
            creator,
            _metadata(provider_id="d.provider", repo="https://x"),
            [_contract("d.contract")],
        )
        registry.deprecate(log, creator, "d.provider")
        assert registry.provider("d.provider").status == "deprecated"
        assert registry.has_contract("d.contract", "^1.0") is True

    def test_transition_on_unknown_provider_rejected(self, creator, log):
        registry = CapabilityRegistry(creator)
        with pytest.raises(RegistryError):
            registry.revoke(log, creator, "ghost.provider")


# ---------------------------------------------------------------------------
# Authority (ADR-003/007) — NAT-02
# ---------------------------------------------------------------------------


class TestAuthority:
    def test_nat_02_non_creator_add_rejected_registry_unchanged(self, creator, log):
        """NAT-02 (spec §134.3): a forged capability.provider_added signed by a
        key that is not the registry's creator anchor must never project into
        the creator-anchored registry. The registry stays exactly the seed set."""
        from jarvis.kernel.capability_registry import _make_approval

        registry = CapabilityRegistry(creator)
        _seed(registry, log, creator)

        other_creator = CreatorIdentity.create(log.db_path + "_other")
        forged_payload = {
            **_metadata(provider_id="evil.provider", repo="https://evil").model_dump(),
            "contracts": [_contract("evil.contract").model_dump()],
        }
        forged_payload["approval"] = _make_approval(
            other_creator, "capability.provider_added", forged_payload
        )
        log.append(
            Event(
                event_id="01F0RGED000000000000000002",
                stream_id="capability",
                event_type="capability.provider_added",
                schema_version=1,
                principal_id=other_creator.fingerprint(),
                ts_utc="2026-09-15T00:00:00Z",
                payload=forged_payload,
            )
        )

        with pytest.raises(RegistryAuthorityError):
            CapabilityRegistry.from_log(log, creator)
        # The seeded registry the creator had already built is untouched.
        assert [p.provider_id for p in registry.providers()] == [
            "fs.local", "http.client", "model.local", "terminal.local",
        ]
        assert registry.has_contract("evil.contract", "^1.0") is False

    def test_nat_02_replay_of_forged_event_halts(self, creator, log):
        """A forged provider_added event (signed with a different key) injected
        directly into the log must halt projection with RegistryAuthorityError."""
        registry = CapabilityRegistry(creator)
        _seed(registry, log, creator)

        from jarvis.kernel.capability_registry import _make_approval
        from jarvis.kernel.event_log import Event

        other_creator = CreatorIdentity.create(log.db_path + "_other_forge")
        forged_payload = {
            **_metadata(provider_id="evil.provider", repo="https://evil").model_dump(),
            "contracts": [_contract("evil.contract").model_dump()],
        }
        forged_payload["approval"] = _make_approval(
            other_creator, "capability.provider_added", forged_payload
        )
        log.append(
            Event(
                event_id="01F0RGED000000000000000001",
                stream_id="capability",
                event_type="capability.provider_added",
                schema_version=1,
                principal_id=other_creator.fingerprint(),
                ts_utc="2026-09-15T00:00:00Z",
                payload=forged_payload,
            )
        )
        with pytest.raises(RegistryAuthorityError):
            CapabilityRegistry.from_log(log, creator)

    def test_anchor_mismatch_rejected(self, creator, log):
        registry = CapabilityRegistry(creator)
        other = CreatorIdentity.create(log.db_path + "_anchor_keys")
        with pytest.raises(RegistryAuthorityError):
            registry.add(
                log,
                other,  # not the registry's anchor
                _metadata(),
                [_contract()],
            )

    def test_unsigned_authority_event_rejected_on_replay(self, creator, log):
        """A provider_added event with no approval field must halt replay."""
        registry = CapabilityRegistry(creator)
        _seed(registry, log, creator)
        log.append(
            Event(
                event_id="01HAAAAAAAAAAAAAAAAAAAAAAA",
                stream_id="capability",
                event_type="capability.provider_added",
                schema_version=1,
                principal_id="attacker",
                ts_utc="2026-09-15T00:00:00Z",
                payload={"provider_id": "unsigned.provider"},
            )
        )
        with pytest.raises(RegistryAuthorityError):
            CapabilityRegistry.from_log(log, creator)

    def test_valid_signature_from_anchor_accepted(self, creator, log):
        registry = CapabilityRegistry(creator)
        registry.add(
            log,
            creator,
            _metadata(provider_id="anon.provider", repo="https://x"),
            [_contract("anon.contract")],
        )
        rebuilt = CapabilityRegistry.from_log(log, creator)
        assert rebuilt.has_contract("anon.contract", "^1.0") is True


# ---------------------------------------------------------------------------
# validate_proposal integration (module 3 + module 4)
# ---------------------------------------------------------------------------


class TestValidateProposalIntegration:
    def test_seeded_registry_satisfies_proposal(self, creator, log):
        registry = CapabilityRegistry(creator)
        _seed(registry, log, creator)
        proposal = ContractProposal(
            contracts=[
                ContractSeed(
                    id="fs.read",
                    version_constraint="^1.0",
                    args={"path": "/project"},
                ),
            ],
            required_capabilities=["READ_FS"],
            intent_id="integration-1",
        )
        result = validate_proposal(proposal, registry, ["READ_FS"])
        assert isinstance(result, Manifest)
        assert result.contracts[0].version == "1.0.0"

    def test_seeded_registry_rejects_unknown_contract(self, creator, log):
        registry = CapabilityRegistry(creator)
        _seed(registry, log, creator)
        proposal = ContractProposal(
            contracts=[
                ContractSeed(
                    id="browser.navigate", version_constraint="^1.0", args={}
                ),
            ],
            required_capabilities=["NET_BROWSER"],
            intent_id="integration-2",
        )
        result = validate_proposal(proposal, registry, ["NET_BROWSER"])
        assert isinstance(result, ValidationFailure)
        assert result.reason == "unknown_contract"

    def test_seeded_registry_rejects_bad_args(self, creator, log):
        registry = CapabilityRegistry(creator)
        _seed(registry, log, creator)
        proposal = ContractProposal(
            contracts=[
                ContractSeed(
                    id="fs.read",
                    version_constraint="^1.0",
                    args={"path": 42},  # wrong type
                ),
            ],
            required_capabilities=["READ_FS"],
            intent_id="integration-3",
        )
        result = validate_proposal(proposal, registry, ["READ_FS"])
        assert isinstance(result, ValidationFailure)
        assert result.reason == "invalid_args"

    def test_nat_01_against_real_registry(self, creator, log):
        """NAT-01 binding against the real registry: ungranted capability in a
        proposal against the seeded catalog is rejected."""
        registry = CapabilityRegistry(creator)
        _seed(registry, log, creator)
        proposal = ContractProposal(
            contracts=[
                ContractSeed(
                    id="fs.write",
                    version_constraint="^1.0",
                    args={"path": "/self", "content": "escalate"},
                ),
            ],
            required_capabilities=["ADMIN"],
            intent_id="nat-01-registry",
        )
        result = validate_proposal(proposal, registry, ["WRITE_FS"])
        assert isinstance(result, ValidationFailure)
        assert result.reason == "ungranted_capability"
        assert not isinstance(result, Manifest)


# ---------------------------------------------------------------------------
# Determinism / replay
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_idempotent_rebuild(self, creator, log):
        registry = CapabilityRegistry(creator)
        _seed(registry, log, creator)
        rebuilt_a = CapabilityRegistry.from_log(log, creator)
        rebuilt_b = CapabilityRegistry.from_log(log, creator)
        assert [p.provider_id for p in rebuilt_a.providers()] == [
            p.provider_id for p in rebuilt_b.providers()
        ]
        for pa, pb in zip(rebuilt_a.providers(), rebuilt_b.providers()):
            assert pa.status == pb.status
            assert pa.registration == pb.registration

    def test_replay_twice_same_digest(self, creator, log):
        registry = CapabilityRegistry(creator)
        _seed(registry, log, creator)
        assert log.projection_digest() == log.projection_digest()