from __future__ import annotations

"""Intent ABI and deterministic static validation (module 3).

Per spec §80.1–80.5 and ADR-002 (model-proposed, determinism-disposed).
No model calls. No effect execution. Produces manifests or refusals only.

Design decisions (resolved ambiguities):

1. Principal / EntityRef / Provenance (spec §80.1):
   None of these have defined modules yet. M1 shape:
   - Intent.principal_id: str
   - Intent.subject_refs: list[str]
   - Intent.provenance: dict[str, Any]
   Flagged: if upstream schemas define Principal or EntityRef, Intent will
   be refactored. No downstream consumers depend on the dict form in M1.

2. risk_class: Literal["safe", "moderate", "high", "critical"].
   Most specific typed option without building a separate enum module.
   Default: "safe" (lowest autonomy level).

3. budget: {tokens: int | None, wall_seconds: int | None, usd: float | None}.
   No enforcement in M1. Enforcement lives in FSM / capsule (module 10).
   Default: all None (unconstrained).

4. manifest_id / intent_id generation: imported from event_log.new_ulid().
   Module coupling: intent.py imports new_ulid and _canonical_json from
   event_log. Accepted in M1 per explicit prompt instruction (the ULID
   helper must not be duplicated). If event_log is refactored into a
   shared utils module later, this import moves.

5. ContractProposal carries intent_id (str | None, default None) and
   risk_class (RiskClass, default "safe") on top of the four fields
   listed in §80.5. Rationale: validate_proposal's fixed signature
   (proposal, catalog, granted_capabilities) has no other channel to
   pass intent context, but Manifest must reference its originating
   intent_id and risk_class. When intent_id is None a ULID is generated
   as a fallback (documented; never happens in normal M1 flow since the
   caller always builds proposals from intents).

6. Manifest.created_at_utc: UTC ISO-8601 timestamp generated at
   validation time. manifest_sha256 covers created_at_utc, so the SAME
   proposal does NOT yield byte-identical manifests across restarts.
   Determinism applies to pass/fail validation and argument schema
   checking, not to temporal identity fields. ULID uniqueness makes
   manifests inherently non-replayable (correct by design).

7. DAG edge semantics (check 4): contract A "depends on" contract B if
   any string value in A.args equals B.id (direct string match) or any
   element of a list value in A.args equals B.id. In M1 no other
   dependency declaration mechanism exists; registry provider-level
   dependencies are out of scope. An empty proposal is vacuously a DAG.

8. Args schema dialect (M1): dict mapping field name → descriptor dict.
   Supported descriptor keys:
     - type: "string" | "integer" | "number" | "boolean" | "array"
             | "object" | "null"
     - required: bool (default False)
     - enum: list (optional; value must be one of)
   If schema is empty dict {}: args must also be empty.
   Extra keys in args not present in schema are rejected.
"""

import datetime as _dt
import hashlib
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .event_log import _canonical_json, new_ulid


# ---------------------------------------------------------------------------
# Clock (minimal local duplicate — avoids importing SystemClock from event_log)
# ---------------------------------------------------------------------------

class _SystemClock:
    """Internal clock; duplicated from event_log.SystemClock to keep the
    import boundary tight (the prompt permits importing _canonical_json and
    new_ulid only)."""

    def now_utc_iso(self) -> str:
        return (
            _dt.datetime.now(_dt.timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )


_clock = _SystemClock()


# ---------------------------------------------------------------------------
# Risk class
# ---------------------------------------------------------------------------

RiskClass = Literal["safe", "moderate", "high", "critical"]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class Budget(BaseModel):
    """Budget envelope. No enforcement in M1 — FSM / capsule work (module 10)."""

    model_config = ConfigDict(extra="forbid")

    tokens: int | None = None
    wall_seconds: int | None = None
    usd: float | None = None


class Intent(BaseModel):
    """§80.1 Intent ABI.

    Simplifications from spec: principal_id is a string (not Principal),
    subject_refs is list[str] (not list[EntityRef]), provenance is a dict.
    """

    model_config = ConfigDict(extra="forbid")

    intent_id: str
    principal_id: str
    objective: str
    domain: str
    subject_refs: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    requested_outcome: dict[str, Any] = Field(default_factory=dict)
    risk_class: RiskClass = "safe"
    provenance: dict[str, Any] = Field(default_factory=dict)
    work_order_id: str | None = None


class ContractSeed(BaseModel):
    """A single contract in a proposal, before version resolution."""

    model_config = ConfigDict(extra="forbid")

    id: str
    version_constraint: str
    args: dict[str, Any] = Field(default_factory=dict)


class ContractProposal(BaseModel):
    """Model-proposed contract set per §80.5.

    Fields beyond the four explicitly listed in the spec (contracts,
    constraints, required_capabilities, budget): intent_id and risk_class
    are carried through to Manifest (see ambiguity #5 in module docstring).
    """

    model_config = ConfigDict(extra="forbid")

    contracts: list[ContractSeed] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    required_capabilities: list[str] = Field(default_factory=list)
    budget: Budget = Field(default_factory=Budget)
    intent_id: str | None = None
    risk_class: RiskClass = "safe"


class ResolvedContract(BaseModel):
    """A contract after version resolution — appears in the Manifest."""

    model_config = ConfigDict(extra="forbid")

    id: str
    version: str
    args: dict[str, Any] = Field(default_factory=dict)


class Manifest(BaseModel):
    """Frozen, hashed execution contract. §80.5.

    manifest_sha256 is computed over canonical JSON of the full body
    (excluding manifest_sha256 itself). Frozen → immutable.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_id: str
    intent_id: str
    contracts: list[ResolvedContract]
    required_capabilities: list[str]
    budget: Budget
    constraints: dict[str, Any]
    risk_class: RiskClass
    manifest_sha256: str
    created_at_utc: str


# ---------------------------------------------------------------------------
# ValidationFailure
# ---------------------------------------------------------------------------

class ValidationFailure(BaseModel):
    """Typed refusal. §80.5 failure → intent.rejected."""

    model_config = ConfigDict(extra="forbid")

    reason: Literal[
        "unknown_contract",
        "unresolvable_version",
        "invalid_args",
        "dependency_cycle",
        "ungranted_capability",
    ]
    detail: str
    contract_id: str | None = None


# ---------------------------------------------------------------------------
# ContractCatalog Protocol (interface only — registry is module 4)
# ---------------------------------------------------------------------------

class ContractCatalog(Protocol):
    """Shape the capability registry will satisfy. Do NOT implement here."""

    def has_contract(self, contract_id: str, version_constraint: str) -> bool: ...
    def resolve_version(self, contract_id: str, version_constraint: str) -> str | None: ...
    def get_args_schema(self, contract_id: str, resolved_version: str) -> dict[str, Any]: ...


# ---------------------------------------------------------------------------
# Args validation — M1 dialect
# ---------------------------------------------------------------------------

_TYPE_NAMES = frozenset({
    "string", "integer", "number", "boolean", "array", "object", "null",
})

_PYTHON_TO_SCHEMA = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}


def _validate_args_value(
    value: Any,
    descriptor: dict[str, Any],
    path: str,
    errors: list[str],
) -> None:
    """Validate a single arg value against its schema descriptor."""
    type_name = descriptor.get("type")
    if type_name is not None:
        if type_name not in _TYPE_NAMES:
            errors.append(f"{path}: schema declares unknown type '{type_name}'")
            return
        actual = _PYTHON_TO_SCHEMA.get(type(value))
        if actual != type_name:
            errors.append(f"{path}: expected type '{type_name}', got '{actual}'")
            return
    enum_vals = descriptor.get("enum")
    if enum_vals is not None and value not in enum_vals:
        errors.append(f"{path}: value {value!r} not in enum {enum_vals}")


def _validate_args(args: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Validate args against the M1 args-schema dialect.

    Returns a list of error strings (empty = valid).
    """
    errors: list[str] = []
    schema_keys = set(schema.keys())
    for key in args:
        if key not in schema_keys:
            errors.append(f"args.{key}: unexpected field (not in schema)")
    for key, descriptor in schema.items():
        if not isinstance(descriptor, dict):
            errors.append(f"schema.{key}: descriptor must be a dict")
            continue
        is_required = descriptor.get("required", False)
        if key not in args:
            if is_required:
                errors.append(f"args.{key}: required field missing")
            continue
        _validate_args_value(args[key], descriptor, f"args.{key}", errors)
    return errors


# ---------------------------------------------------------------------------
# DAG helpers
# ---------------------------------------------------------------------------

def _find_args_contract_refs(
    args: dict[str, Any],
    proposal_ids: set[str],
) -> set[str]:
    """Return proposal contract ids referenced directly in args values."""
    refs: set[str] = set()
    for v in args.values():
        if isinstance(v, str) and v in proposal_ids:
            refs.add(v)
        elif isinstance(v, list):
            for elem in v:
                if isinstance(elem, str) and elem in proposal_ids:
                    refs.add(elem)
    return refs


def _has_cycle(
    adj: dict[str, set[str]],
    node: str,
    visited: set[str],
    stack: set[str],
) -> bool:
    visited.add(node)
    stack.add(node)
    for neighbor in adj.get(node, set()):
        if neighbor not in visited:
            if _has_cycle(adj, neighbor, visited, stack):
                return True
        elif neighbor in stack:
            return True
    stack.discard(node)
    return False


def _detect_cycle(ids: list[str], adj: dict[str, set[str]]) -> str | None:
    """Return a node in a cycle, or None if acyclic."""
    visited: set[str] = set()
    for node in ids:
        if node not in visited:
            if _has_cycle(adj, node, visited, set()):
                return node
    return None


# ---------------------------------------------------------------------------
# validate_proposal
# ---------------------------------------------------------------------------

def validate_proposal(
    proposal: ContractProposal,
    catalog: ContractCatalog,
    granted_capabilities: list[str] | set[str],
) -> Manifest | ValidationFailure:
    """Deterministic static validation per §80.5 and ADR-002.

    Checks (in order):
      1. Every contract id exists in catalog.
      2. Every version constraint resolves to a concrete version.
      3. Every contract's args validate against its args schema.
      4. The dependency graph between contracts is a DAG (args-level refs).
      5. required_capabilities ⊆ granted_capabilities.

    On success: Manifest with SHA-256 over canonical JSON body.
    On failure: ValidationFailure with reason code and detail.
    """
    granted = set(granted_capabilities)
    contract_ids: list[str] = [c.id for c in proposal.contracts]
    id_set = set(contract_ids)

    # --- check 1: contract existence ---
    for seed in proposal.contracts:
        if not catalog.has_contract(seed.id, seed.version_constraint):
            return ValidationFailure(
                reason="unknown_contract",
                detail=f"contract '{seed.id}' not found in catalog",
                contract_id=seed.id,
            )

    # --- check 2: version resolution ---
    resolved_contracts: list[ResolvedContract] = []
    for seed in proposal.contracts:
        ver = catalog.resolve_version(seed.id, seed.version_constraint)
        if ver is None:
            return ValidationFailure(
                reason="unresolvable_version",
                detail=(
                    f"contract '{seed.id}' version '{seed.version_constraint}' "
                    "could not be resolved"
                ),
                contract_id=seed.id,
            )
        resolved_contracts.append(
            ResolvedContract(id=seed.id, version=ver, args=seed.args)
        )

    # --- check 3: args schema validation ---
    for rc in resolved_contracts:
        schema = catalog.get_args_schema(rc.id, rc.version)
        if not schema:
            # No schema declared for this contract — skip args validation.
            # A catalog that omits a schema imposes no arg constraints.
            continue
        errors = _validate_args(rc.args, schema)
        if errors:
            return ValidationFailure(
                reason="invalid_args",
                detail=f"contract '{rc.id}' args failed schema: {'; '.join(errors)}",
                contract_id=rc.id,
            )

    # --- check 4: DAG dependency check ---
    adj: dict[str, set[str]] = {}
    for seed in proposal.contracts:
        refs = _find_args_contract_refs(seed.args, id_set)
        refs.discard(seed.id)  # self-refs ignored
        adj[seed.id] = refs
    cycle_node = _detect_cycle(contract_ids, adj)
    if cycle_node is not None:
        return ValidationFailure(
            reason="dependency_cycle",
            detail=f"contract '{cycle_node}' participates in a dependency cycle",
            contract_id=cycle_node,
        )

    # --- check 5: capability subset ---
    required_set = set(proposal.required_capabilities)
    missing = required_set - granted
    if missing:
        return ValidationFailure(
            reason="ungranted_capability",
            detail=f"required capabilities not granted: {', '.join(sorted(missing))}",
            contract_id=None,
        )

    # --- build manifest ---
    manifest_id = new_ulid()
    intent_id = proposal.intent_id or new_ulid()
    created_at = _clock.now_utc_iso()

    body_dict: dict[str, Any] = {
        "manifest_id": manifest_id,
        "intent_id": intent_id,
        "contracts": [rc.model_dump() for rc in resolved_contracts],
        "required_capabilities": proposal.required_capabilities,
        "budget": proposal.budget.model_dump(),
        "constraints": proposal.constraints,
        "risk_class": proposal.risk_class,
        "created_at_utc": created_at,
    }
    manifest_sha256 = hashlib.sha256(_canonical_json(body_dict)).hexdigest()

    return Manifest(
        manifest_id=manifest_id,
        intent_id=intent_id,
        contracts=resolved_contracts,
        required_capabilities=proposal.required_capabilities,
        budget=proposal.budget,
        constraints=proposal.constraints,
        risk_class=proposal.risk_class,
        manifest_sha256=manifest_sha256,
        created_at_utc=created_at,
    )
