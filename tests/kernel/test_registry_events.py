from __future__ import annotations

"""F5 registry event writer tests (creator 2026-09-18 decision, Option 1).

The capability registry emits `capability.provider_added` /
`capability.provider_revoked` events when constructed with an `EventLog`;
without one, behavior is the pre-F5 in-memory only behavior. Writer task
only — no from_log / replay-projection (that is module 7).
"""

import pytest

from jarvis.kernel.creator import AuthorityUnavailable
from jarvis.kernel.event_log import EventLog
from jarvis.kernel.registry import (
    CREATOR_PRINCIPAL_ID,
    CapabilityRegistry,
    ContractDef,
    ProviderBinding,
    ProviderMeta,
    RegistryError,
)


def _binding(provider_id: str = "test.provider") -> ProviderBinding:
    return ProviderBinding(
        meta=ProviderMeta(
            provider_id=provider_id,
            version="1.0.0",
            license="MIT",
            license_compatibility="approved",
            adapter="jarvis.adapters.test",
            trust_level="sandboxed",
            process_model="subprocess",
            network="none",
            health_check="test: probe",
            cve_status="checked_clean",
            provenance_added_by=CREATOR_PRINCIPAL_ID,
            provenance_added_at_utc="2026-09-16T00:00:00Z",
            provenance_reason="F5 registry-events test",
        ),
        contracts=[
            ContractDef(
                contract_id="test.read",
                version="1.0.0",
                args_schema={"path": {"type": "string", "required": True}},
            )
        ],
    )


def _log(tmp_path) -> EventLog:
    return EventLog(db_path=str(tmp_path / "log.db"))


# ---------------------------------------------------------------------------
# provider_added
# ---------------------------------------------------------------------------

def test_register_with_log_appends_single_provider_added(tmp_path):
    log = _log(tmp_path)
    registry = CapabilityRegistry(log=log)

    registry.register_provider(CREATOR_PRINCIPAL_ID, _binding("test.provider"))

    events = log.replay()
    assert [e.event_type for e in events] == ["capability.provider_added"]
    ev = events[0]
    assert ev.stream_id == "capability"
    assert ev.principal_id == CREATOR_PRINCIPAL_ID
    assert ev.payload["principal_id"] == CREATOR_PRINCIPAL_ID
    assert ev.payload["provider"]["meta"]["provider_id"] == "test.provider"
    # round-trip: the event payload reconstructs the exact binding
    assert ProviderBinding.model_validate(ev.payload["provider"]) == _binding(
        "test.provider"
    )
    assert log.verify_chain() is True


def test_register_without_log_appends_nothing(tmp_path):
    log = _log(tmp_path)
    registry = CapabilityRegistry()  # no log passed

    assert registry._log is None  # noqa: SLF001
    registry.register_provider(CREATOR_PRINCIPAL_ID, _binding())
    assert registry.get_provider("test.provider") is not None
    # nothing was written anywhere: the untouched log has zero events
    assert log.replay() == []
    assert log.last_seq() == 0


def test_seed_with_log_emits_four_provider_added(tmp_path):
    log = _log(tmp_path)

    CapabilityRegistry.seed_m1_defaults(log=log)

    events = log.replay()
    assert [e.event_type for e in events] == ["capability.provider_added"] * 4
    assert log.verify_chain() is True
    assert [e.payload["provider"]["meta"]["provider_id"] for e in events] == [
        "fs.default",
        "terminal.default",
        "model.adapter",
        "http.default",
    ]


def test_seed_without_log_emits_nothing_and_stays_functional(tmp_path):
    log = _log(tmp_path)

    registry = CapabilityRegistry.seed_m1_defaults()

    assert registry._log is None  # noqa: SLF001
    assert registry.resolve_provider("model.generate_structured", "^1.0") == "model.adapter"
    assert log.replay() == []


# ---------------------------------------------------------------------------
# rejected registrations append nothing
# ---------------------------------------------------------------------------

def test_non_creator_registration_appends_nothing(tmp_path):
    log = _log(tmp_path)
    registry = CapabilityRegistry(log=log)

    with pytest.raises(AuthorityUnavailable):
        registry.register_provider("intruder", _binding())

    assert log.replay() == []
    assert log.last_seq() == 0


def test_empty_args_schema_registration_appends_nothing(tmp_path):
    log = _log(tmp_path)
    registry = CapabilityRegistry(log=log)

    bad = _binding("bad.provider")
    bad.contracts[0].args_schema = {}
    with pytest.raises(RegistryError):
        registry.register_provider(CREATOR_PRINCIPAL_ID, bad)

    assert log.replay() == []
    assert log.last_seq() == 0


# ---------------------------------------------------------------------------
# revoke
# ---------------------------------------------------------------------------

def test_revoke_creator_only(tmp_path):
    log = _log(tmp_path)
    registry = CapabilityRegistry(log=log)
    registry.register_provider(CREATOR_PRINCIPAL_ID, _binding("test.provider"))

    with pytest.raises(AuthorityUnavailable):
        registry.revoke_provider("test.provider", "intruder")

    assert registry.get_provider("test.provider") is not None  # unchanged
    assert [e.event_type for e in log.replay()] == ["capability.provider_added"]


def test_revoke_removes_provider_from_all_resolution_paths(tmp_path):
    log = _log(tmp_path)
    registry = CapabilityRegistry(log=log)
    registry.register_provider(CREATOR_PRINCIPAL_ID, _binding("test.provider"))

    registry.revoke_provider("test.provider", CREATOR_PRINCIPAL_ID)

    events = log.replay()
    assert [e.event_type for e in events] == [
        "capability.provider_added",
        "capability.provider_revoked",
    ]
    assert events[-1].payload == {
        "provider_id": "test.provider",
        "principal_id": CREATOR_PRINCIPAL_ID,
    }
    assert log.verify_chain() is True
    # typed negative results, never an exception, never a stale binding
    assert registry.get_provider("test.provider") is None
    assert registry.resolve_provider("test.read", "^1.0") is None
    assert registry.resolve_version("test.read", "^1.0") is None
    assert registry.get_args_schema("test.read", "1.0.0") == {}
    assert registry.has_contract("test.read", "^1.0") is False


def test_revoke_unknown_or_already_revoked_is_typed_error_no_event(tmp_path):
    log = _log(tmp_path)
    registry = CapabilityRegistry(log=log)
    registry.register_provider(CREATOR_PRINCIPAL_ID, _binding("test.provider"))

    with pytest.raises(RegistryError):
        registry.revoke_provider("ghost", CREATOR_PRINCIPAL_ID)
    registry.revoke_provider("test.provider", CREATOR_PRINCIPAL_ID)
    with pytest.raises(RegistryError):
        registry.revoke_provider("test.provider", CREATOR_PRINCIPAL_ID)

    assert [e.event_type for e in log.replay()] == [
        "capability.provider_added",
        "capability.provider_revoked",
    ]
    assert log.verify_chain() is True


def test_revoke_then_reregister_appends_at_end(tmp_path):
    log = _log(tmp_path)
    registry = CapabilityRegistry(log=log)
    registry.register_provider(CREATOR_PRINCIPAL_ID, _binding("a"))
    registry.register_provider(CREATOR_PRINCIPAL_ID, _binding("b"))

    registry.revoke_provider("a", CREATOR_PRINCIPAL_ID)
    registry.register_provider(CREATOR_PRINCIPAL_ID, _binding("a"))

    # "a" was revoked, so "b" is now first-registered and wins resolution;
    # the re-registered "a" sits at the end of the order.
    assert registry.resolve_provider("test.read", "^1.0") == "b"
    assert [e.event_type for e in log.replay()] == [
        "capability.provider_added",
        "capability.provider_added",
        "capability.provider_revoked",
        "capability.provider_added",
    ]
    assert log.verify_chain() is True