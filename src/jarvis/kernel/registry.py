from __future__ import annotations

"""Capability registry (module 4) and ProviderAdapter Protocol interface.

Per §131.2 the registry sits between stable capability contracts and
JARVIS-owned provider adapters. This module provides:

1. `ProviderAdapter` — the Protocol interface JARVIS-owned adapters will
   implement (modules 6/8). Interface ONLY; no implementations live here.
2. `ProviderMeta` / `ContractDef` / `ProviderBinding` — pydantic v2 schemas
   (extra="forbid") carrying the §131.4 supply-chain metadata and the
   §131.19 behavioral profile.
3. `CapabilityRegistry` — an in-memory registry satisfying the
   `ContractCatalog` Protocol from `jarvis.kernel.intent`, so
   `validate_proposal` can run end-to-end against the seeded M1 providers.

M1 design decisions (resolved ambiguities, see §105.1, §131.2–131.4):

1. Registry is IN-MEMORY in M1. §131.2 describes the registry as a
   projection over `capability.*` events; that event-sourced persistence
   is DEFERRED (a later module). M1 seeds the same 4 providers
   (§105.1) every boot via `seed_m1_defaults()` and has no mutation API
   except creator-only `register_provider`. There is no log write, no
   events table dependency, and no disk state. (Ambiguity #1 from the
   gate review — reported, not silently resolved.)

2. Trust model is principal_id equality IN M1 (ADR-003). `register_provider`
   accepts only the creator principal, identified by `CREATOR_PRINCIPAL_ID`
   == "creator". The key file is NOT read; no signature is verified. This
   is the explicit M1 trust model and MUST be replaced by verifiable
   creator signatures in a later module (the NAT-02 signature half).

3. Args-schema invariant (closes the module-3 fail-open). Every
   `ContractDef` registered in the registry MUST declare a non-empty
   `args_schema`. `register_provider` enforces this and raises a typed
   `RegistryError` otherwise. Consequently a properly seeded registry can
   never expose a schema-less contract, so `validate_proposal`'s
   skip-when-empty behavior is only a defensive fallback for defective
   catalogs, never a supported configuration. (Freebuff flag 1 from the
   module-3 gate.)

4. Version constraint dialect (M1): `version_constraint` is treated as a
   string filter — exact match OR caret-prefix match, where a constraint
   "^1" / "^1.0" / "^1.0.0" matches every version whose first component
   equals the integer after the caret ("^1.0" matches "1.0.0" and
   "1.5.0" but not "2.0.0"). No semver library; this narrow dialect is
   documented, not expanded. (Ambiguity #3 — reported, not expanded.)

5. First-registered wins. If multiple providers expose the same
   contract_id and a matching constraint, the first provider registered
   owns resolution for M1. The seed set has no overlaps, so this rule
   exists for containment and is documented, not engineered around.

6. Trust boundary is PROVIDER-LEVEL only. §131.3 describes a contract
   trust_boundary, but the M1 schema places `trust_level` on the provider
   (`ProviderMeta`). No contract-level trust field is added. (Ambiguity #4
   — reported, not added.)
"""

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .creator import AuthorityUnavailable
from .intent import ContractCatalog


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class RegistryError(RuntimeError):
    """Base error for the capability registry."""


# ---------------------------------------------------------------------------
# ProviderAdapter Protocol (interface ONLY — modules 6/8 implement)
# ---------------------------------------------------------------------------

class ProviderAdapter(Protocol):
    """JARVIS-owned adapter bound to a registered provider.

    Implemented by the model adapter (module 6) and the fs/terminal/http
    adapters (module 8). No implementation lives in this module.
    """

    @property
    def provider_id(self) -> str: ...

    async def invoke(self, contract_id: str, version: str, args: dict[str, Any]) -> dict[str, Any]: ...

    def health_check(self) -> bool: ...


# ---------------------------------------------------------------------------
# Schemas (extra="forbid")
# ---------------------------------------------------------------------------

class ProviderMeta(BaseModel):
    """Supply-chain metadata per §131.4."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    version: str
    commit: str | None = None                       # pinned commit or digest
    license: str
    license_compatibility: Literal["approved", "review_required", "forbidden"]
    adapter: str                                    # dotted path string; not imported here
    trust_level: Literal["trusted", "sandboxed", "isolated"]
    process_model: Literal["in_process", "subprocess", "container", "remote"]
    network: Literal["none", "egress_only", "bidirectional"]
    health_check: str                               # descriptive strategy name
    cve_status: Literal["unchecked", "checked_clean", "checked_flagged"]
    last_audit_utc: str | None = None
    provenance_added_by: str
    provenance_added_at_utc: str
    provenance_reason: str
    fallback_provider_id: str | None = None


class ContractDef(BaseModel):
    """A capability contract a provider exposes (M1 args-schema dialect)."""

    model_config = ConfigDict(extra="forbid")

    contract_id: str
    version: str                                    # resolved concrete version e.g. "1.0.0"
    args_schema: dict[str, Any]                     # M1 dialect, same as intent.py
    behavioral_profile: dict[str, Any] = Field(default_factory=dict)  # §131.19


class ProviderBinding(BaseModel):
    """A registered provider with at least one exposed contract."""

    model_config = ConfigDict(extra="forbid")

    meta: ProviderMeta
    contracts: list[ContractDef]                    # at least one (enforced at registration)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

CREATOR_PRINCIPAL_ID = "creator"


class CapabilityRegistry(ContractCatalog):
    """In-memory capability registry (M1).

    Satisfies the `ContractCatalog` Protocol consumed by
    `intent.validate_proposal`. Constructor takes no providers; build the
    M1 registry with `seed_m1_defaults()`. Writes are creator-only
    (`register_provider`), fail fast, and are unavailable outside the
    creator principal.
    """

    def __init__(self) -> None:
        self._bindings: dict[str, ProviderBinding] = {}   # provider_id -> binding
        self._order: list[str] = []                        # registration order

    # ---- registration -----------------------------------------------------

    def register_provider(self, principal_id: str, binding: ProviderBinding) -> None:
        """Register a provider (creator-only, ADR-003).

        M1 trust model: identity check is principal_id == CREATOR_PRINCIPAL_ID.
        The key file is not read. To be replaced by signature verification in
        a later module.

        Enforces the args-schema invariant: every ContractDef MUST declare a
        non-empty args_schema (§131.4 + Freebuff flag 1).
        """
        if principal_id != CREATOR_PRINCIPAL_ID:
            raise AuthorityUnavailable(
                f"provider registration rejected: principal '{principal_id}' "
                f"is not the creator principal '{CREATOR_PRINCIPAL_ID}'"
            )
        if not binding.contracts:
            raise RegistryError(
                f"provider '{binding.meta.provider_id}' declares no contracts"
            )
        for contract in binding.contracts:
            if not contract.args_schema:
                raise RegistryError(
                    f"contract {contract.contract_id} missing args_schema"
                )
        provider_id = binding.meta.provider_id
        if provider_id not in self._bindings:
            self._order.append(provider_id)
        self._bindings[provider_id] = binding

    # ---- ContractCatalog Protocol (consumed by intent.py) ------------------

    def _candidates_for(self, contract_id: str) -> list[tuple[str, ContractDef]]:
        """(provider_id, ContractDef) pairs exposing contract_id, in
        registration order (first-registered wins)."""
        result: list[tuple[str, ContractDef]] = []
        for provider_id in self._order:
            binding = self._bindings.get(provider_id)
            if binding is None:
                continue
            for contract in binding.contracts:
                if contract.contract_id == contract_id:
                    result.append((provider_id, contract))
        return result

    def has_contract(self, contract_id: str, version_constraint: str) -> bool:
        return any(
            self._constraint_matches(contract.version, version_constraint)
            for _, contract in self._candidates_for(contract_id)
        )

    def resolve_version(self, contract_id: str, version_constraint: str) -> str | None:
        for _, contract in self._candidates_for(contract_id):
            if self._constraint_matches(contract.version, version_constraint):
                return contract.version
        return None

    def get_args_schema(self, contract_id: str, resolved_version: str) -> dict[str, Any]:
        """Args schema of the winning provider for that concrete version."""
        for _, contract in self._candidates_for(contract_id):
            if contract.version == resolved_version:
                return contract.args_schema
        return {}

    @staticmethod
    def _constraint_matches(version: str, constraint: str) -> bool:
        """M1 dialect: exact match OR caret-prefix match.

        "^1" / "^1.0" / "^1.0.0" matches any version whose first component
        equals the integer after the caret. No semver library (documented).
        """
        constraint = constraint.strip()
        if constraint.startswith("^"):
            major = constraint[1:].split(".", 1)[0].strip()
            if not major.isdigit():
                return False
            return version.split(".", 1)[0] == major
        return version == constraint

    # ---- seeding (§105.1) -------------------------------------------------

    @classmethod
    def seed_m1_defaults(
        cls, creator_principal_id: str = CREATOR_PRINCIPAL_ID
    ) -> "CapabilityRegistry":
        """Build the M1 registry with the 4 seeded providers (§105.1),
        registered by the creator principal."""
        registry = cls()
        registry.register_provider(
            creator_principal_id,
            ProviderBinding(
                meta=ProviderMeta(
                    provider_id="fs.default",
                    version="1.0.0",
                    commit=None,
                    license="MIT",
                    license_compatibility="approved",
                    adapter="jarvis.adapters.filesystem",
                    trust_level="sandboxed",
                    process_model="subprocess",
                    network="none",
                    health_check="fs.default: probe",
                    cve_status="checked_clean",
                    last_audit_utc="2026-09-15T00:00:00Z",
                    provenance_added_by=creator_principal_id,
                    provenance_added_at_utc="2026-09-15T00:00:00Z",
                    provenance_reason="M1 seed per spec §105.1",
                    fallback_provider_id=None,
                ),
                contracts=[
                    ContractDef(
                        contract_id="fs.read",
                        version="1.0.0",
                        args_schema={"path": {"type": "string", "required": True}},
                    ),
                    ContractDef(
                        contract_id="fs.write",
                        version="1.0.0",
                        args_schema={"path": {"type": "string", "required": True}},
                    ),
                ],
            ),
        )
        registry.register_provider(
            creator_principal_id,
            ProviderBinding(
                meta=ProviderMeta(
                    provider_id="terminal.default",
                    version="1.0.0",
                    commit=None,
                    license="MIT",
                    license_compatibility="approved",
                    adapter="jarvis.adapters.terminal",
                    trust_level="sandboxed",
                    process_model="subprocess",
                    network="none",
                    health_check="terminal.default: echo probe",
                    cve_status="checked_clean",
                    last_audit_utc="2026-09-15T00:00:00Z",
                    provenance_added_by=creator_principal_id,
                    provenance_added_at_utc="2026-09-15T00:00:00Z",
                    provenance_reason="M1 seed per spec §105.1",
                    fallback_provider_id=None,
                ),
                contracts=[
                    ContractDef(
                        contract_id="terminal.execute",
                        version="1.0.0",
                        args_schema={
                            "cmd": {"type": "string", "required": True},
                            "cwd": {"type": "string", "required": False},
                        },
                    ),
                ],
            ),
        )
        registry.register_provider(
            creator_principal_id,
            ProviderBinding(
                meta=ProviderMeta(
                    provider_id="model.adapter",
                    version="1.0.0",
                    commit=None,
                    license="MIT",
                    license_compatibility="review_required",
                    adapter="jarvis.adapters.model",
                    trust_level="sandboxed",
                    process_model="remote",
                    network="egress_only",
                    health_check="model.adapter: health endpoint probe",
                    cve_status="unchecked",
                    last_audit_utc=None,
                    provenance_added_by=creator_principal_id,
                    provenance_added_at_utc="2026-09-15T00:00:00Z",
                    provenance_reason=(
                        "M1 stub; module 6 binds the real backend (Groq or "
                        "equivalent) after the model-backend decision"
                    ),
                    fallback_provider_id=None,
                ),
                contracts=[
                    ContractDef(
                        contract_id="model.generate_structured",
                        version="1.0.0",
                        args_schema={
                            "role_contract": {"type": "string", "required": True},
                            "schema_id": {"type": "string", "required": True},
                        },
                    ),
                ],
            ),
        )
        registry.register_provider(
            creator_principal_id,
            ProviderBinding(
                meta=ProviderMeta(
                    provider_id="http.default",
                    version="1.0.0",
                    commit=None,
                    license="MIT",
                    license_compatibility="approved",
                    adapter="jarvis.adapters.http",
                    trust_level="trusted",
                    process_model="in_process",
                    network="egress_only",
                    health_check="http.default: egress deny by default",
                    cve_status="checked_clean",
                    last_audit_utc="2026-09-15T00:00:00Z",
                    provenance_added_by=creator_principal_id,
                    provenance_added_at_utc="2026-09-15T00:00:00Z",
                    provenance_reason="M1 seed per spec §105.1",
                    fallback_provider_id=None,
                ),
                contracts=[
                    ContractDef(
                        contract_id="http.get",
                        version="1.0.0",
                        args_schema={"url": {"type": "string", "required": True}},
                    ),
                    ContractDef(
                        contract_id="http.post",
                        version="1.0.0",
                        args_schema={"url": {"type": "string", "required": True}},
                    ),
                ],
            ),
        )
        return registry

    # ---- inspection -------------------------------------------------------

    def list_contracts(self) -> list[tuple[str, str]]:
        """(contract_id, version) pairs in registration order (deduplicated)."""
        seen: set[tuple[str, str]] = set()
        result: list[tuple[str, str]] = []
        for provider_id in self._order:
            binding = self._bindings.get(provider_id)
            if binding is None:
                continue
            for contract in binding.contracts:
                pair = (contract.contract_id, contract.version)
                if pair not in seen:
                    seen.add(pair)
                    result.append(pair)
        return result

    def get_provider(self, provider_id: str) -> ProviderBinding | None:
        return self._bindings.get(provider_id)

    def resolve_provider(
        self, contract_id: str, version_constraint: str
    ) -> str | None:
        """Return the winning provider_id for a contract (first-registered),
        or None. Additive method (module 6 seam-gap fix, pre-approved);
        same first-registered-wins rule as resolve_version."""
        for provider_id, contract in self._candidates_for(contract_id):
            if self._constraint_matches(contract.version, version_constraint):
                return provider_id
        return None