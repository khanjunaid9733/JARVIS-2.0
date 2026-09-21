from __future__ import annotations

"""L5 Router and Role Contracts (ORCHESTRATOR_ARCHITECTURE.md §10).

Roles are capability contracts, not provider names:
    IMPLEMENTER          -> implementation.v1
    RED_TEAM_REVIEWER    -> redteam.v1
    INDEPENDENT_VERIFIER -> verification.v1
    RECONCILER           -> reconciliation.v1

Enforces Invariant I5 (Exclusion Constraint):
    For any package P:
        provider_filling(redteam.v1, P) != provider_filling(verification.v1, P)

When every provider for a required role is unavailable or excluded, the router
returns a DEGRADED result and the package HOLDS.
"""

import enum
from dataclasses import dataclass, field
from typing import Mapping, Sequence


class Role(str, enum.Enum):
    """Declared roles in the autonomous development pipeline."""

    IMPLEMENTER = "IMPLEMENTER"
    RED_TEAM_REVIEWER = "RED_TEAM_REVIEWER"
    INDEPENDENT_VERIFIER = "INDEPENDENT_VERIFIER"
    RECONCILER = "RECONCILER"


class Capability(str, enum.Enum):
    """Semantic versioned capability contracts."""

    IMPLEMENTATION_V1 = "implementation.v1"
    REDTEAM_V1 = "redteam.v1"
    VERIFICATION_V1 = "verification.v1"
    RECONCILIATION_V1 = "reconciliation.v1"


ROLE_CAPABILITIES: Mapping[Role, Capability] = {
    Role.IMPLEMENTER: Capability.IMPLEMENTATION_V1,
    Role.RED_TEAM_REVIEWER: Capability.REDTEAM_V1,
    Role.INDEPENDENT_VERIFIER: Capability.VERIFICATION_V1,
    Role.RECONCILER: Capability.RECONCILIATION_V1,
}


@dataclass(frozen=True)
class ProviderProfile:
    """Declared capabilities and behavioral health of a provider."""

    name: str
    capabilities: frozenset[Capability]
    healthy: bool = True
    priority: int = 100  # Lower number = higher preference


@dataclass(frozen=True)
class RoleAssignment:
    """Historical assignment of a provider to a role for a package."""

    package: str
    role: Role
    provider: str


@dataclass(frozen=True)
class RouterResult:
    """Outcome of provider resolution."""

    provider: str | None
    degraded: bool = False
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.provider is not None and not self.degraded


def default_provider_registry() -> dict[str, ProviderProfile]:
    """Default baseline provider capabilities per spec §10."""
    return {
        "bigpickle": ProviderProfile(
            name="bigpickle",
            capabilities=frozenset({
                Capability.IMPLEMENTATION_V1,
                Capability.RECONCILIATION_V1,
            }),
            priority=10,
        ),
        "freebuff": ProviderProfile(
            name="freebuff",
            capabilities=frozenset({
                Capability.REDTEAM_V1,
            }),
            priority=20,
        ),
        "antigravity": ProviderProfile(
            name="antigravity",
            capabilities=frozenset({
                Capability.REDTEAM_V1,
                Capability.VERIFICATION_V1,
            }),
            priority=30,
        ),
    }


class Router:
    """L5 Provider Router with Invariant I5 enforcement."""

    def __init__(
        self, registry: Mapping[str, ProviderProfile] | None = None
    ) -> None:
        self._registry = dict(registry if registry is not None else default_provider_registry())

    def resolve(
        self,
        role: Role,
        package: str,
        assignments: Sequence[RoleAssignment] = (),
    ) -> RouterResult:
        """Resolve the best eligible provider for a given role and package.

        Enforces:
        1. Required capability match
        2. Provider health
        3. Invariant I5 (no provider fills both RED_TEAM_REVIEWER and
           INDEPENDENT_VERIFIER on the same package)
        """
        required_cap = ROLE_CAPABILITIES[role]

        # Determine excluded providers per Invariant I5
        excluded: set[str] = set()
        if role is Role.RED_TEAM_REVIEWER:
            for a in assignments:
                if a.package == package and a.role is Role.INDEPENDENT_VERIFIER:
                    excluded.add(a.provider)
        elif role is Role.INDEPENDENT_VERIFIER:
            for a in assignments:
                if a.package == package and a.role is Role.RED_TEAM_REVIEWER:
                    excluded.add(a.provider)

        # Filter candidates
        candidates: list[ProviderProfile] = []
        for p in self._registry.values():
            if not p.healthy:
                continue
            if required_cap not in p.capabilities:
                continue
            if p.name in excluded:
                continue
            candidates.append(p)

        if not candidates:
            exclusion_note = f" (excluded: {sorted(excluded)})" if excluded else ""
            return RouterResult(
                provider=None,
                degraded=True,
                reason=(
                    f"No healthy provider available for {role.value} "
                    f"requiring {required_cap.value}{exclusion_note}"
                ),
            )

        # Sort by priority
        candidates.sort(key=lambda p: p.priority)
        chosen = candidates[0]
        return RouterResult(provider=chosen.name)
