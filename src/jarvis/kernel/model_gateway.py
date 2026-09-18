from __future__ import annotations

"""Model Gateway — role-contract-aware structured generation (module 6).

Per §131.11–131.13 and ADR-001 / ADR-006 / ADR-004. The gateway is the
authoritative seam between kernel policy and any model provider:

    MODEL ROLE CONTRACT
        ↓
    MODEL REGISTRY            ← consumed via ProviderResolver (registry.py)
        ↓
    MODEL ADAPTER             ← runtime dispatch via {provider_id -> ProviderAdapter}
        ↓
    MODEL PROVIDER / BACKEND

M1 scope: `SCHEMA_CONSTRAINED` (`generate_structured`) is the only routed
role. All §131.13 roles are declared in `RoleContract`, but only
`SCHEMA_CONSTRAINED` has a bound contract in `M1_ROLE_CONTRACTS`; the rest
return `TypedFailure(reason="unsupported_contract")` until a later module
binds them. Role → contract/constraint is DATA (`M1_ROLE_CONTRACTS`),
never branching code.

ADR-006: structured output = Pydantic v2 schema validation with
retry-on-validation-failure. The model never supplies validated data; the
gateway validates locally (`schema.model_validate`). On `ValidationError`
the error text is appended as `feedback` to the next adapter request
(self-correction), capped at `max_attempts`.

ADR-001 seam: the gateway never imports a provider client; adapters
implement the `ProviderAdapter` Protocol from `jarvis.kernel.registry`.
Transport-level failures are mapped to the typed `ProviderTransportError`
defined here (adapters import it). Decision disclosed: the transport
exception lives in `model_gateway.py` (not `registry.py`) so `registry.py`
changes only by the single pre-approved additive `resolve_provider` method.

No effects, no tools: this module proposes; it does not dispose. It makes
no calls to fs/terminal/http capability adapters. The `egress_only`
transport call of the bound model adapter is the only outbound traffic
(authorized by the `model.adapter` provider declaration).
"""

from enum import StrEnum
from typing import Any, Generic, Literal, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from ..observability import (
    SPAN_MODEL_CALL,
    SPAN_REGISTRY_RESOLVE,
    NoOpObserver,
)
from .registry import ProviderAdapter, ProviderBinding


# ---------------------------------------------------------------------------
# Transport seam (ADR-001)
# ---------------------------------------------------------------------------

class ProviderTransportError(RuntimeError):
    """Typed transport failure raised by adapters at the provider boundary.

    Adapters import this from the gateway so the kernel maps any network /
    HTTP / protocol failure to `TypedFailure(reason="transport_error")`
    without catching raw client exceptions.
    """


# ---------------------------------------------------------------------------
# Role contracts (§131.13 exact identifiers)
# ---------------------------------------------------------------------------

class RoleContract(StrEnum):
    EXECUTE_REASONING = "execute_reasoning"
    PLAN = "plan"
    CODE = "code"
    CLASSIFY = "classify"
    VISION = "vision"
    STT = "stt"
    TTS = "tts"
    EMBED = "embed"
    RERANK = "rerank"
    PII_DETECT = "pii_detect"
    SCHEMA_CONSTRAINED = "schema_constrained"
    ROBOTICS_PERCEPTION = "robotics_perception"
    VLA_VLN = "vla_vln"
    SIMULATION_WORLD_MODEL = "simulation_world_model"
    SPECIALIST = "specialist"


# Role → (contract_id, version_constraint). Only SCHEMA_CONSTRAINED is M1-routed.
M1_ROLE_CONTRACTS: dict[RoleContract, tuple[str, str]] = {
    RoleContract.SCHEMA_CONSTRAINED: ("model.generate_structured", "^1.0"),
}


# ---------------------------------------------------------------------------
# Protocols / result types
# ---------------------------------------------------------------------------

class ProviderResolver(Protocol):
    """Metadata layer of the substitution seam (satisfied by CapabilityRegistry).

    Two layers keep metadata (registry) and runtime dispatch (adapter map)
    separate: resolve to a provider_id, then look up its binding for
    contract version / fallback metadata. Adapter instances never live in
    the registry.
    """

    def resolve_provider(self, contract_id: str, version_constraint: str) -> str | None: ...

    def resolve_version(self, contract_id: str, version_constraint: str) -> str | None: ...

    def get_provider(self, provider_id: str) -> ProviderBinding | None: ...


class TypedFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reason: Literal[
        "no_provider",
        "unsupported_contract",
        "transport_error",
        "validation_exhausted",
        "adapter_error",
        "schema_error",
        "authority_unavailable",
    ]
    detail: str
    attempts: int = 0


T = TypeVar("T", bound="BaseModel")


class ValidatedOutput(BaseModel, Generic[T]):
    """Locally validated model output (ADR-006). value is NEVER model-trusted;

    the gateway constructed it via `schema.model_validate(raw)`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: T
    role_contract: RoleContract
    provider_id: str
    contract_id: str
    contract_version: str
    attempts: int


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------

class ModelGateway:
    """Deterministic seam between kernel policy and model providers.

    Constructor takes the metadata resolver and the runtime adapter map;
    provider resolution goes through the resolver, dispatch through the
    adapter map. Never hardcodes a provider id.
    """

    def __init__(
        self,
        resolver: ProviderResolver,
        adapters: dict[str, ProviderAdapter],
        *,
        max_attempts: int = 3,
        observer: Any | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self._resolver = resolver
        self._adapters = dict(adapters)
        self._max_attempts = max_attempts
        self._observer = observer or NoOpObserver()

    def _span(self, name: str, attributes: dict[str, Any] | None = None) -> Any:
        return self._observer.span(name, attributes or {})

    async def generate_structured(
        self,
        role_contract: RoleContract,
        schema: type[BaseModel],
        *,
        schema_id: str | None = None,
        intent_id: str | None = None,
        task_id: str | None = None,
    ) -> ValidatedOutput | TypedFailure:
        route = M1_ROLE_CONTRACTS.get(role_contract)
        if route is None:
            return TypedFailure(
                reason="unsupported_contract",
                detail=(
                    f"role '{role_contract.value}' is declared (§131.13) but "
                    "has no M1-bound provider (module 6 routes only "
                    "SCHEMA_CONSTRAINED)"
                ),
            )
        contract_id, version_constraint = route

        with self._span(
            SPAN_REGISTRY_RESOLVE,
            {"contract.id": contract_id, "contract.version": version_constraint},
        ) as resolve_span:
            provider_id = self._resolver.resolve_provider(
                contract_id, version_constraint
            )
            if provider_id is None:
                return TypedFailure(
                    reason="no_provider",
                    detail=f"no registered provider for {contract_id}@{version_constraint}",
                )
            resolve_span.set_attribute("provider.id", provider_id)
            binding = self._resolver.get_provider(provider_id)
            if binding is None:
                return TypedFailure(
                    reason="adapter_error",
                    detail=f"resolver returned provider_id {provider_id!r} with no binding",
                )

            contract_version = self._resolver.resolve_version(
                contract_id, version_constraint
            )
            if contract_version is None:
                return TypedFailure(
                    reason="no_provider",
                    detail=(
                        f"resolver returned provider_id {provider_id!r} but no "
                        f"matching version for {contract_id}@{version_constraint}"
                    ),
                )

        adapter, active_provider_id = self._select_adapter(binding)
        if adapter is None:
            return TypedFailure(
                reason="adapter_error",
                detail=(
                    f"no adapter bound for provider_id {provider_id!r}"
                    + (
                        f" or fallback {binding.meta.fallback_provider_id!r}"
                        if binding.meta.fallback_provider_id
                        else ""
                    )
                ),
            )

        resolve_schema_id = schema_id or schema.__name__
        feedback: list[str] = []

        for attempt in range(1, self._max_attempts + 1):
            args: dict[str, Any] = {
                "role_contract": role_contract.value,
                "schema_id": resolve_schema_id,
                "schema_json": schema.model_json_schema(),
                "intent_id": intent_id,
                "task_id": task_id,
                "feedback": list(feedback),
            }
            with self._span(
                SPAN_MODEL_CALL,
                {
                    "model.name": active_provider_id,
                    "contract.id": contract_id,
                    "contract.version": contract_version,
                    "prompt.version": resolve_schema_id,
                },
            ):
                try:
                    raw = await adapter.invoke(contract_id, contract_version, args)
                except ProviderTransportError as exc:
                    return TypedFailure(
                        reason="transport_error",
                        detail=str(exc),
                        attempts=attempt,
                    )
                except Exception as exc:  # adapter contract violation
                    return TypedFailure(
                        reason="adapter_error",
                        detail=f"{type(exc).__name__}: {exc}",
                        attempts=attempt,
                    )

            try:
                value = schema.model_validate(raw)
            except ValidationError as exc:  # model output failed validation
                feedback.append(f"{type(exc).__name__}: {exc}")
                continue
            except Exception as exc:  # schema/validator defect, not model noise
                return TypedFailure(
                    reason="schema_error",
                    detail=(
                        f"{type(exc).__name__}: {exc} (schema/validator defect; "
                        "model output never shipped as feedback)"
                    ),
                    attempts=attempt,
                )

            return ValidatedOutput(
                value=value,
                role_contract=role_contract,
                provider_id=active_provider_id,
                contract_id=contract_id,
                contract_version=contract_version,
                attempts=attempt,
            )

        return TypedFailure(
            reason="validation_exhausted",
            detail=(
                f"model output failed validation after {self._max_attempts} "
                "attempts; last error sent back as feedback"
            ),
            attempts=self._max_attempts,
        )

    def _select_adapter(
        self, binding: ProviderBinding
    ) -> tuple[ProviderAdapter | None, str]:
        """Pick the runtime adapter: primary, else fallback (ADR-004/provenance)."""
        primary = binding.meta.provider_id
        if primary in self._adapters:
            return self._adapters[primary], primary
        fallback = binding.meta.fallback_provider_id
        if fallback and fallback in self._adapters:
            return self._adapters[fallback], fallback
        return None, primary


# ---------------------------------------------------------------------------
# Production wiring (option (b) of the module-6 prompt registry binding)
# ---------------------------------------------------------------------------

def register_groq_provider(
    registry: Any,
    *,
    creator_principal_id: str = "creator",
    provider_id: str = "model.adapter",
) -> None:
    """Creator-authorized production binding: point `model.adapter` at the
    real Groq OpenAI-compatible backend.

    Option (b) from the module-6 prompt: `seed_m1_defaults` stays the test
    fixture; this helper overwrites the seeded `model.adapter` stub with
    the real binding for production wiring (registry.register_provider
    replaces by provider_id). `registry` is imported lazily to keep this
    module dependency-light; callers always pass a CapabilityRegistry.
    """
    from .registry import ContractDef, ProviderBinding, ProviderMeta

    registry.register_provider(
        creator_principal_id,
        ProviderBinding(
            meta=ProviderMeta(
                provider_id=provider_id,
                version="1.0.0",
                commit=None,
                license="MIT",
                license_compatibility="review_required",
                adapter="jarvis.providers.openai_compatible",
                trust_level="sandboxed",
                process_model="remote",
                network="egress_only",
                health_check="model.adapter: OpenAI-compatible /models probe",
                cve_status="unchecked",
                last_audit_utc=None,
                provenance_added_by=creator_principal_id,
                provenance_added_at_utc="2026-09-16T00:00:00Z",
                provenance_reason=(
                    "module 6: real backend bound (Groq, OpenAI-compatible "
                    "endpoint from JARVIS_MODEL_BASE_URL); cve/audit still "
                    "unchecked, review before promote"
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