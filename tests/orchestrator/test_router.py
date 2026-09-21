from __future__ import annotations

"""Unit tests for L5 Router & Invariant I5 (tests/orchestrator/test_router.py).

I5 is enforced on CANONICAL identities. Comparing raw strings let a case
variant, an alias for the same logical worker, or a differently-spelled package
id defeat the constraint entirely (F-M3.3-FB-4), so every comparison folds
casing, whitespace and known aliases first.
"""

from jarvis.orchestrator.router import (
    Capability,
    ProviderProfile,
    Role,
    RoleAssignment,
    Router,
    canonical_package,
    canonical_provider,
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


# ---------------------------------------------------------------------------
# Canonical identity (F-M3.3-FB-4)
# ---------------------------------------------------------------------------


def test_canonical_provider_folds_case_whitespace_and_aliases() -> None:
    assert canonical_provider("Antigravity") == "antigravity"
    assert canonical_provider("  AGY ") == "antigravity"
    assert canonical_provider("gemini") == "antigravity"
    assert canonical_provider("DeepSeek") == "freebuff"
    assert canonical_provider("opencode") == "bigpickle"
    # An unknown provider still folds case/whitespace, and stays distinct.
    assert canonical_provider(" Someone New ") == "someone new"


def test_canonical_package_folds_case_and_whitespace() -> None:
    assert canonical_package(" M3.3 ") == "m3.3"
    assert canonical_package("M3.3") == canonical_package("m3.3")


def test_i5_excludes_a_case_variant_of_the_verifying_provider() -> None:
    prior = [
        RoleAssignment(package="M3.3", role=Role.RED_TEAM_REVIEWER, provider="Antigravity")
    ]
    result = Router().resolve(Role.INDEPENDENT_VERIFIER, package="M3.3", assignments=prior)
    assert not result.ok and result.degraded


def test_i5_excludes_an_alias_of_the_red_teaming_provider() -> None:
    registry = {
        "agy": ProviderProfile(
            name="agy",
            capabilities=frozenset({Capability.VERIFICATION_V1}),
            priority=10,
        )
    }
    prior = [
        RoleAssignment(package="M3.3", role=Role.RED_TEAM_REVIEWER, provider="antigravity")
    ]
    result = Router(registry=registry).resolve(
        Role.INDEPENDENT_VERIFIER, package="M3.3", assignments=prior
    )
    assert not result.ok and result.degraded


def test_i5_excludes_across_a_package_case_variant() -> None:
    prior = [
        RoleAssignment(package="m3.3", role=Role.RED_TEAM_REVIEWER, provider="antigravity")
    ]
    result = Router().resolve(Role.INDEPENDENT_VERIFIER, package="M3.3", assignments=prior)
    assert not result.ok and result.degraded


def test_i5_does_not_over_exclude_a_different_provider() -> None:
    prior = [
        RoleAssignment(package="M3.3", role=Role.RED_TEAM_REVIEWER, provider="freebuff")
    ]
    result = Router().resolve(Role.INDEPENDENT_VERIFIER, package="M3.3", assignments=prior)
    assert result.ok and result.provider == "antigravity"
