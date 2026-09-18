from __future__ import annotations

"""Module 11 bootstrap tests (spec §127.1 idempotency requirements)."""

from jarvis.bootstrap import CoreService, ensure_service_started, new_pairing_code

SEEDED = ["fs.default", "http.default", "model.adapter", "terminal.default"]


def test_start_seeds_four_providers_and_identity(tmp_path):
    service = CoreService(home=tmp_path).start()
    try:
        assert service.provider_ids() == SEEDED
        assert service.projection().event_count == 4
        assert len(service.fingerprint) == 8
        assert service.log_path == tmp_path / "log.db"
        assert (tmp_path / "keys" / "creator.ed25519").exists()
    finally:
        service.close()


def test_restart_is_idempotent_and_identity_stable(tmp_path):
    first = CoreService(home=tmp_path).start()
    count_1 = first.projection().event_count
    fingerprint_1 = first.fingerprint
    first.close()

    second = CoreService(home=tmp_path).start()
    try:
        assert second.projection().event_count == count_1 == 4
        assert second.fingerprint == fingerprint_1
        assert second.provider_ids() == SEEDED
    finally:
        second.close()


def test_restart_reconstructs_registry_without_new_events(tmp_path):
    CoreService(home=tmp_path).start().close()

    service = CoreService(home=tmp_path).start()
    try:
        assert service.registry is not None
        assert service.registry.get_provider("model.adapter") is not None
        assert service.registry.get_provider("agent.rogue") is None
        assert service.projection().event_count == 4
    finally:
        service.close()


def test_service_marker_is_idempotent(tmp_path):
    service = CoreService(home=tmp_path).start()
    try:
        assert ensure_service_started(service.log) is True
        assert ensure_service_started(service.log) is False
        assert service.log.last_seq() == 5
    finally:
        service.close()


def test_pairing_code_format_is_ambiguity_free():
    for _ in range(20):
        code = new_pairing_code()
        left, right = code.split("-")
        assert len(left) == len(right) == 4
        assert all(c in "ABCDEFGHJKLMNPQRSTUVWXYZ23456789" for c in left + right)
