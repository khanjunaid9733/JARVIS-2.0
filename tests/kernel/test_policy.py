from __future__ import annotations

"""Module 9 policy tests (§80.5). Pure deterministic decisions; no effects.

Policy evaluates a frozen Manifest against an explicit PolicyContext. It
never calls a model and never executes an effect; the only side effect is
the optional `policy.check` event.
"""

from jarvis.kernel.event_log import EventLog
from jarvis.kernel.intent import Budget, Manifest, ResolvedContract
from jarvis.kernel.policy import (
    CHECK_NAMES,
    AutonomyLevel,
    BudgetLimits,
    PolicyContext,
    PolicyDecision,
    PolicyEngine,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _manifest(*, required=("READ_FS",), risk="safe", budget=None, contracts=None):
    return Manifest(
        manifest_id="m-1",
        intent_id="i-1",
        contracts=contracts
        if contracts is not None
        else [ResolvedContract(id="fs.read", version="1.0.0", args={})],
        required_capabilities=list(required),
        budget=budget or Budget(),
        constraints={},
        risk_class=risk,
        manifest_sha256="0" * 64,
        created_at_utc="2026-09-18T00:00:00Z",
    )


def _context(
    *,
    granted=("READ_FS",),
    autonomy=AutonomyLevel.L3,
    privacy="internal",
    trust=None,
    mission_limits=None,
    creator_limits=None,
):
    return PolicyContext(
        principal_id="creator",
        granted_capabilities=frozenset(granted),
        autonomy_level=autonomy,
        creator_limits=creator_limits or BudgetLimits(),
        mission_limits=mission_limits or BudgetLimits(),
        privacy_class=privacy,
        contract_trust_levels=trust
        if trust is not None
        else {"fs.read": "sandboxed"},
    )


# ---------------------------------------------------------------------------
# Allow path
# ---------------------------------------------------------------------------

def test_allow_when_all_checks_pass():
    decision = PolicyEngine().evaluate(_manifest(), _context())

    assert decision.allowed is True
    assert decision.denials == []
    assert tuple(decision.checks) == CHECK_NAMES
    assert all(decision.checks.values())


# ---------------------------------------------------------------------------
# capability_grantable
# ---------------------------------------------------------------------------

def test_capability_not_granted_is_denied():
    decision = PolicyEngine().evaluate(
        _manifest(required=("READ_FS", "WRITE_FS")),
        _context(granted=("READ_FS",)),
    )

    assert decision.allowed is False
    assert [d.reason for d in decision.denials] == ["capability_not_granted"]
    assert "WRITE_FS" in decision.denials[0].detail
    assert decision.checks["capability_grantable"] is False
    assert decision.checks["risk_within_autonomy"] is True


# ---------------------------------------------------------------------------
# budget_within_limits
# ---------------------------------------------------------------------------

def test_budget_exceeded_mission_limit_is_denied():
    decision = PolicyEngine().evaluate(
        _manifest(budget=Budget(tokens=5000)),
        _context(mission_limits=BudgetLimits(max_tokens=1000)),
    )

    assert decision.allowed is False
    assert [d.reason for d in decision.denials] == ["budget_exceeded"]
    assert "tokens=5000" in decision.denials[0].detail


def test_budget_exceeded_creator_limit_is_denied():
    decision = PolicyEngine().evaluate(
        _manifest(budget=Budget(usd=10.0)),
        _context(creator_limits=BudgetLimits(max_usd=5.0)),
    )

    assert decision.allowed is False
    assert [d.reason for d in decision.denials] == ["budget_exceeded"]


def test_budget_within_when_limits_unset():
    decision = PolicyEngine().evaluate(
        _manifest(budget=Budget(tokens=999999, wall_seconds=999999, usd=999.0)),
        _context(),
    )

    assert decision.allowed is True
    assert decision.checks["budget_within_limits"] is True


# ---------------------------------------------------------------------------
# risk_within_autonomy (§59)
# ---------------------------------------------------------------------------

def test_high_risk_requires_l4():
    denied = PolicyEngine().evaluate(
        _manifest(risk="high"), _context(autonomy=AutonomyLevel.L3)
    )
    assert denied.allowed is False
    assert [d.reason for d in denied.denials] == ["risk_exceeds_autonomy"]

    allowed = PolicyEngine().evaluate(
        _manifest(risk="high"), _context(autonomy=AutonomyLevel.L4)
    )
    assert allowed.allowed is True


def test_critical_risk_requires_l5():
    assert (
        PolicyEngine()
        .evaluate(_manifest(risk="critical"), _context(autonomy=AutonomyLevel.L4))
        .allowed
        is False
    )
    assert (
        PolicyEngine()
        .evaluate(_manifest(risk="critical"), _context(autonomy=AutonomyLevel.L5))
        .allowed
        is True
    )


def test_safe_risk_allowed_at_l3():
    decision = PolicyEngine().evaluate(
        _manifest(risk="safe"), _context(autonomy=AutonomyLevel.L3)
    )
    assert decision.allowed is True
    assert decision.checks["risk_within_autonomy"] is True


# ---------------------------------------------------------------------------
# privacy_trust_match
# ---------------------------------------------------------------------------

def test_restricted_privacy_requires_trusted_provider():
    denied = PolicyEngine().evaluate(
        _manifest(), _context(privacy="restricted", trust={"fs.read": "sandboxed"})
    )
    assert denied.allowed is False
    assert [d.reason for d in denied.denials] == ["privacy_trust_mismatch"]

    allowed = PolicyEngine().evaluate(
        _manifest(), _context(privacy="restricted", trust={"fs.read": "trusted"})
    )
    assert allowed.allowed is True


def test_internal_privacy_requires_sandboxed_provider():
    denied = PolicyEngine().evaluate(
        _manifest(), _context(privacy="internal", trust={"fs.read": "isolated"})
    )
    assert [d.reason for d in denied.denials] == ["privacy_trust_mismatch"]

    allowed = PolicyEngine().evaluate(
        _manifest(), _context(privacy="internal", trust={"fs.read": "sandboxed"})
    )
    assert allowed.allowed is True


def test_public_privacy_needs_no_trust_levels():
    decision = PolicyEngine().evaluate(
        _manifest(), _context(privacy="public", trust={})
    )
    assert decision.allowed is True
    assert decision.checks["privacy_trust_match"] is True


def test_unknown_or_missing_trust_fails_closed():
    missing = PolicyEngine().evaluate(
        _manifest(), _context(privacy="restricted", trust={})
    )
    assert [d.reason for d in missing.denials] == ["privacy_trust_mismatch"]
    assert "no trust level" in missing.denials[0].detail

    unknown = PolicyEngine().evaluate(
        _manifest(), _context(privacy="restricted", trust={"fs.read": "platinum"})
    )
    assert [d.reason for d in unknown.denials] == ["privacy_trust_mismatch"]
    assert "unknown trust level" in unknown.denials[0].detail


# ---------------------------------------------------------------------------
# Multiple failures report all denials
# ---------------------------------------------------------------------------

def test_multiple_failures_report_every_denial():
    decision = PolicyEngine().evaluate(
        _manifest(
            required=("READ_FS", "WRITE_FS"),
            risk="high",
            budget=Budget(tokens=5000),
        ),
        _context(
            granted=("READ_FS",),
            autonomy=AutonomyLevel.L3,
            mission_limits=BudgetLimits(max_tokens=1000),
            privacy="restricted",
            trust={"fs.read": "sandboxed"},
        ),
    )

    assert decision.allowed is False
    assert [d.reason for d in decision.denials] == [
        "capability_not_granted",
        "budget_exceeded",
        "risk_exceeds_autonomy",
        "privacy_trust_mismatch",
    ]
    assert all(d is False for d in decision.checks.values())


# ---------------------------------------------------------------------------
# Determinism (§111)
# ---------------------------------------------------------------------------

def test_identical_inputs_yield_identical_decisions():
    manifest = _manifest()
    context = _context()
    assert PolicyEngine().evaluate(manifest, context) == PolicyEngine().evaluate(
        manifest, context
    )


# ---------------------------------------------------------------------------
# Events / side effects
# ---------------------------------------------------------------------------

def test_one_policy_check_event_per_evaluation(tmp_path):
    log = EventLog(db_path=str(tmp_path / "log.db"))
    engine = PolicyEngine(log=log)

    engine.evaluate(_manifest(), _context())

    events = log.replay()
    assert [e.event_type for e in events] == ["policy.check"]
    assert events[0].stream_id == "policy"
    assert events[0].principal_id == "creator"
    assert events[0].payload["policy_result"] == "allow"
    assert events[0].payload["capability_requested"] == ["READ_FS"]
    assert events[0].payload["manifest_id"] == "m-1"
    assert log.verify_chain() is True


def test_deny_event_payload_carries_denials(tmp_path):
    log = EventLog(db_path=str(tmp_path / "log.db"))
    engine = PolicyEngine(log=log)

    engine.evaluate(
        _manifest(required=("READ_FS", "WRITE_FS")), _context(granted=("READ_FS",))
    )

    payload = log.replay()[-1].payload
    assert payload["policy_result"] == "deny"
    assert payload["denials"][0]["reason"] == "capability_not_granted"


def test_repeated_evaluations_produce_deterministic_payloads(tmp_path):
    log = EventLog(db_path=str(tmp_path / "log.db"))
    engine = PolicyEngine(log=log)
    manifest = _manifest()
    context = _context()

    engine.evaluate(manifest, context)
    engine.evaluate(manifest, context)

    events = log.replay()
    assert len(events) == 2
    assert dict(events[0].payload) == dict(events[1].payload)
    assert log.verify_chain() is True


def test_log_none_is_fully_in_memory():
    engine = PolicyEngine()

    assert engine._log is None  # noqa: SLF001
    decision = engine.evaluate(_manifest(), _context())
    assert isinstance(decision, PolicyDecision)
    assert decision.allowed is True


# ---------------------------------------------------------------------------
# F-B6: empty-contract manifest is fail-closed under non-public privacy class
# ---------------------------------------------------------------------------

def test_zero_contract_manifest_denied_restricted_privacy():
    manifest = _manifest(contracts=[])
    context = _context(privacy="restricted", trust={})
    decision = PolicyEngine().evaluate(manifest, context)

    assert decision.allowed is False
    assert [d.reason for d in decision.denials] == ["privacy_trust_mismatch"]
    assert decision.checks["privacy_trust_match"] is False


def test_zero_contract_manifest_denied_internal_privacy():
    manifest = _manifest(contracts=[])
    context = _context(privacy="internal", trust={})
    decision = PolicyEngine().evaluate(manifest, context)

    assert decision.allowed is False
    assert [d.reason for d in decision.denials] == ["privacy_trust_mismatch"]


def test_zero_contract_manifest_public_privacy_still_allowed():
    manifest = _manifest(contracts=[])
    context = _context(privacy="public", trust={})
    decision = PolicyEngine().evaluate(manifest, context)

    assert decision.allowed is True
    assert decision.checks["privacy_trust_match"] is True
