from __future__ import annotations

"""Deterministic policy-viability gate (module 9).

Per §80.5 "Policy viability (deterministic)" — the stage between static
validation and the frozen Manifest:

    INTENT → CONTRACT PROPOSAL → STATIC VALIDATION → POLICY VIABILITY
          → MANIFEST → CAPABILITY RESOLUTION

The engine performs exactly four deterministic checks (§80.5):

    capability_grantable   every manifest.required_capabilities ⊆ granted set
    budget_within_limits   manifest.budget within mission AND creator limits
    risk_within_autonomy   risk_class permitted at the declared AutonomyLevel (§59)
    privacy_trust_match    privacy_class compatible with the resolved providers'
                           trust_level (§131.4), supplied per contract

Policy is PURE and SYNCHRONOUS: it decides, it never executes effects and
never calls a model (§79/§80.3). Identical (manifest, context) input yields
an identical PolicyDecision (§111 — no hidden now(), no unstable ordering).
The only side effect is one optional `policy.check` event per evaluation
(stream "policy", §110.1 attributes `capability.requested` / `policy.result`).

Threshold tables (risk→autonomy, privacy→trust) are DATA, not branching.
The spec fixes the check names, not the thresholds; the M1 defaults below
are disclosed in the module-9 report and may be overridden by the creator.

Integration is intentionally NOT wired in this module: policy is a
standalone seam consumed by later orchestration (module 10) / CLI (module
11). `intent.py`, `registry.py`, `event_log.py`, and `effect_envelope.py`
are unchanged.
"""

from enum import IntEnum
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field

from .event_log import Event, EventLog
from .intent import Budget, Manifest


POLICY_STREAM_ID = "policy"
POLICY_EVENT_TYPE = "policy.check"

CHECK_NAMES: tuple[str, ...] = (
    "capability_grantable",
    "budget_within_limits",
    "risk_within_autonomy",
    "privacy_trust_match",
)


# ---------------------------------------------------------------------------
# Autonomy levels (§59)
# ---------------------------------------------------------------------------

class AutonomyLevel(IntEnum):
    L0 = 0  # conversation only
    L1 = 1  # suggest
    L2 = 2  # execute after approval
    L3 = 3  # execute low-risk routine operations
    L4 = 4  # autonomous missions within explicit boundaries
    L5 = 5  # distributed autonomous operation with policy oversight


# Minimum autonomy required by each risk class (M1 default, disclosed).
RISK_MIN_AUTONOMY: dict[str, AutonomyLevel] = {
    "safe": AutonomyLevel.L3,
    "moderate": AutonomyLevel.L3,
    "high": AutonomyLevel.L4,
    "critical": AutonomyLevel.L5,
}

# Trust ordering (§131.4 trust_level: isolated < sandboxed < trusted).
TRUST_RANK: dict[str, int] = {"isolated": 0, "sandboxed": 1, "trusted": 2}

# Minimum provider trust required by each privacy class (M1 default, disclosed).
PRIVACY_MIN_TRUST_RANK: dict[str, int] = {
    "public": 0,
    "internal": 1,
    "confidential": 1,
    "restricted": 2,
}

PrivacyClass = Literal["public", "internal", "confidential", "restricted"]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BudgetLimits(BaseModel):
    """An upper bound envelope. None means "unbounded on this dimension"."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_tokens: int | None = None
    max_wall_seconds: int | None = None
    max_usd: float | None = None


class PolicyContext(BaseModel):
    """Explicit, frozen inputs to a policy decision. No ambient state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    principal_id: str
    granted_capabilities: frozenset[str]
    autonomy_level: AutonomyLevel
    creator_limits: BudgetLimits = Field(default_factory=BudgetLimits)
    mission_limits: BudgetLimits = Field(default_factory=BudgetLimits)
    privacy_class: PrivacyClass = "internal"
    # contract_id -> provider trust_level, pre-resolved via the ADR-001 seam.
    contract_trust_levels: Mapping[str, str] = Field(default_factory=dict)


class PolicyDenial(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: Literal[
        "capability_not_granted",
        "budget_exceeded",
        "risk_exceeds_autonomy",
        "privacy_trust_mismatch",
    ]
    detail: str


class PolicyDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    allowed: bool
    denials: list[PolicyDenial]
    checks: dict[str, bool]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class PolicyEngine:
    """Evaluates policy viability; appends one `policy.check` event per call
    when constructed with an `EventLog` (default None = fully in-memory)."""

    def __init__(self, *, log: EventLog | None = None) -> None:
        self._log = log

    def evaluate(self, manifest: Manifest, context: PolicyContext) -> PolicyDecision:
        denials: list[PolicyDenial] = []
        checks: dict[str, bool] = {}

        # 1. capability_grantable
        missing = sorted(
            set(manifest.required_capabilities) - set(context.granted_capabilities)
        )
        checks["capability_grantable"] = not missing
        if missing:
            denials.append(
                PolicyDenial(
                    reason="capability_not_granted",
                    detail=(
                        f"capabilities not granted to principal "
                        f"{context.principal_id!r}: {missing}"
                    ),
                )
            )

        # 2. budget_within_limits
        violations = self._budget_violations(manifest.budget, context)
        checks["budget_within_limits"] = not violations
        if violations:
            denials.append(
                PolicyDenial(reason="budget_exceeded", detail="; ".join(violations))
            )

        # 3. risk_within_autonomy
        required = RISK_MIN_AUTONOMY[manifest.risk_class]
        risk_ok = context.autonomy_level >= required
        checks["risk_within_autonomy"] = risk_ok
        if not risk_ok:
            denials.append(
                PolicyDenial(
                    reason="risk_exceeds_autonomy",
                    detail=(
                        f"risk_class {manifest.risk_class!r} requires at least "
                        f"{required.name}; mission declared "
                        f"{context.autonomy_level.name}"
                    ),
                )
            )

        # 4. privacy_trust_match
        privacy_detail = self._privacy_violation(manifest, context)
        checks["privacy_trust_match"] = privacy_detail is None
        if privacy_detail is not None:
            denials.append(
                PolicyDenial(reason="privacy_trust_mismatch", detail=privacy_detail)
            )

        decision = PolicyDecision(allowed=not denials, denials=denials, checks=checks)
        self._emit(manifest, context, decision)
        return decision

    # ---- checks -----------------------------------------------------------

    @staticmethod
    def _budget_violations(budget: Budget, context: PolicyContext) -> list[str]:
        violations: list[str] = []
        dimensions = (
            ("tokens", "max_tokens"),
            ("wall_seconds", "max_wall_seconds"),
            ("usd", "max_usd"),
        )
        for field, limit_field in dimensions:
            value = getattr(budget, field)
            if value is None:
                continue
            for label, limits in (
                ("mission", context.mission_limits),
                ("creator", context.creator_limits),
            ):
                limit = getattr(limits, limit_field)
                if limit is not None and value > limit:
                    violations.append(
                        f"{field}={value} exceeds {label} limit {limit}"
                    )
        return violations

    @staticmethod
    def _privacy_violation(
        manifest: Manifest, context: PolicyContext
    ) -> str | None:
        required_rank = PRIVACY_MIN_TRUST_RANK[context.privacy_class]
        if required_rank == 0:
            return None
        for contract in manifest.contracts:
            level = context.contract_trust_levels.get(contract.id)
            if level is None:
                return (
                    f"no trust level supplied for contract {contract.id!r} "
                    f"(privacy class {context.privacy_class!r})"
                )
            rank = TRUST_RANK.get(level)
            if rank is None:
                return f"unknown trust level {level!r} for contract {contract.id!r}"
            if rank < required_rank:
                return (
                    f"contract {contract.id!r} provider trust {level!r} is below "
                    f"the {context.privacy_class!r} requirement"
                )
        return None

    # ---- event ------------------------------------------------------------

    def _emit(
        self, manifest: Manifest, context: PolicyContext, decision: PolicyDecision
    ) -> None:
        if self._log is None:
            return
        payload = {
            "capability_requested": sorted(manifest.required_capabilities),
            "policy_result": "allow" if decision.allowed else "deny",
            "manifest_id": manifest.manifest_id,
            "principal_id": context.principal_id,
            "denials": [d.model_dump() for d in decision.denials],
        }
        self._log.append(
            Event(
                stream_id=POLICY_STREAM_ID,
                event_type=POLICY_EVENT_TYPE,
                principal_id=context.principal_id,
                payload=payload,
            )
        )
