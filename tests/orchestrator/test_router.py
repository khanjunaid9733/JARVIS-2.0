from __future__ import annotations

"""Unit tests for L5 Router & Invariant I5 (tests/orchestrator/test_router.py)."""

import pytest

from jarvis.orchestrator.router import (
    Capability,
    ProviderProfile,
    Role,
    RoleAssignment,
    Router,
    RouterResult,
    default_provider_registry,
)


def test_default_registry_mapping() -> None:
    registry = default_provider_registry()
    assert "bigpickle" in registry
    assert "freebuff" in registry
    assert "antigravity" in registry

    assert Capability.IMPLEMENTATION_V1 in registry["bigpickle"].capabilities
    assert Capability.RECONCILIATION_V1 in registry["bigpickle"].capabilities
    assert Capability.REDTEAM_V1 in registry["freebuff"].capabilities
    assert Capability.REDTEAM_V1 in registry["antigravity"].capabilities
    assert Capability.VERIFICATION_V1 in registry["antigravity"].capabilities


def test_resolve_implementer_selects_bigpickle() -> None:
    router = Router()
    result = router.resolve(Role.IMPLEMENTER, package="M3.3")
    assert result.ok
    assert result.provider == "bigpickle"


def test_resolve_reconciler_selects_bigpickle() -> None:
    router = Router()
    result = router.resolve(Role.RECONCILER, package="M3.3")
    assert result.ok
    assert result.provider == "bigpickle"


def test_resolve_redteam_prefers_freebuff_by_priority() -> None:
    router = Router()
    result = router.resolve(Role.RED_TEAM_REVIEWER, package="M3.3")
    assert result.ok
    assert result.provider == "freebuff"


def test_resolve_verifier_selects_antigravity() -> None:
    router = Router()
    result = router.resolve(Role.INDEPENDENT_VERIFIER, package="M3.3")
    assert result.ok
    assert result.provider == "antigravity"


def test_invariant_i5_verifier_cannot_redteam_same_package() -> None:
    """If Antigravity verified package P, it cannot red-team package P."""
    router = Router()
    # Freebuff is unhealthy, leaving only antigravity as a redteam candidate
    registry = default_provider_registry()
    registry["freebuff"] = ProviderProfile(
        name="freebuff",
        capabilities=frozenset({Capability.REDTEAM_V1}),
        healthy=False,
    )
    router = Router(registry=registry)

    # Prior assignment: antigravity already verified M3.3
    prior = [
        RoleAssignment(package="M3.3", role=Role.INDEPENDENT_VERIFIER, provider="antigravity")
    ]

    # Redteam resolution on M3.3 must exclude antigravity and return DEGRADED
    result = router.resolve(Role.RED_TEAM_REVIEWER, package="M3.3", assignments=prior)
    assert not result.ok
    assert result.degraded
    assert "excluded: ['antigravity']" in result.reason


def test_invariant_i5_redteam_cannot_verify_same_package() -> None:
    """If Antigravity red-teamed package P, it cannot verify package P."""
    router = Router()
    prior = [
        RoleAssignment(package="M3.3", role=Role.RED_TEAM_REVIEWER, provider="antigravity")
    ]

    # Verification on M3.3 must exclude antigravity (the only verifier), thus DEGRADED
    result = router.resolve(Role.INDEPENDENT_VERIFIER, package="M3.3", assignments=prior)
    assert not result.ok
    assert result.degraded
    assert "excluded: ['antigravity']" in result.reason


def test_invariant_i5_allows_different_packages() -> None:
    """Antigravity can red-team package A and verify package B."""
    router = Router()
    prior = [
        RoleAssignment(package="PackageA", role=Role.RED_TEAM_REVIEWER, provider="antigravity")
    ]

    # Verifying PackageB is allowed
    result = router.resolve(Role.INDEPENDENT_VERIFIER, package="PackageB", assignments=prior)
    assert result.ok
    assert result.provider == "antigravity"


def test_degraded_when_no_healthy_provider() -> None:
    registry = {
        "dead_worker": ProviderProfile(
            name="dead_worker",
            capabilities=frozenset({Capability.IMPLEMENTATION_V1}),
            healthy=False,
        )
    }
    router = Router(registry=registry)
    result = router.resolve(Role.IMPLEMENTER, package="M3.3")
    assert not result.ok
    assert result.degraded
    assert "No healthy provider available" in result.reason
