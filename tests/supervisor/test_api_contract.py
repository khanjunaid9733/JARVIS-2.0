"""Contract test - pins the public API surface of ``jarvis.supervisor``.

WHY THIS FILE EXISTS (incident of 2026-09-20)
--------------------------------------------
``tests/supervisor/test_t18_context_drift.py`` was authored against an INVENTED
surface. Five bindings were written from memory rather than from the module:

    bound in the test                          reality
    --------------------------------------     -------------------------------
    from jarvis.supervisor.supervisor          EscalationReason is defined in
        import EscalationReason                ``jarvis.supervisor.authority``
    EvidenceLedger.declare(...)                ``declare`` is a factory on
                                               ``Evidence``, not on the ledger
    PackageSnapshot.declare(...)               same - only ``Evidence.declare``
    EvidenceLedger.FILESYSTEM_RUNG             never existed; the real datum is
                                               ``EvidencePrecedence.FILESYSTEM``
    Supervisor.pure_fold(...)                  never existed; the fold is
                                               ``decide_recovery(...)``

Each ghost surfaced only at pytest runtime, one ImportError/AttributeError at a
time, behind a guess-and-rerun loop. This file makes the surface *readable*: it
turns "invent a method" into a single named failure instead of twenty re-runs.

FOLLOW-UP APPLIED IN THE SAME COMMIT (escalation, not just a pin)
-----------------------------------------------------------------
Two real inconsistencies had been hidden by the incident and are now fixed:

  1. ``jarvis.supervisor.supervisor`` re-exported ``AuthorityTier``,
     ``decide_authority_tier`` and ``is_creator_gated`` but NOT
     ``EscalationReason`` - the single omission that caused the ImportError.
     It is now re-exported.
  2. The package facade omitted ``LifecycleDecision``, ``lifecycle_decision``,
     ``Clock`` and ``BlobReader`` from ``__all__``. ``Clock`` and ``BlobReader``
     are the two dependency-injection seam Protocols, so consumers implementing
     a hermetic clock or a blob reader had no supported import path. All four
     are now facade exports (30 names total).

WHAT IS PINNED
  1. the package facade (``__all__``) and that every export resolves;
  2. the module that DEFINES each public name (the "home" map);
  3. the submodule set;
  4. the dataclass construction surface (field names, in order) of every datum;
  5. enum member sets (frozen decision data - order included);
  6. the parameter shape of every public entry point;
  7. explicit negatives for the names hallucinated in the incident.

Pure introspection: no model calls, no ambient reads, no effects, no clocks.
An intentional API change must update this file in the same commit.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import fields
from enum import Enum

import pytest

import jarvis.supervisor as supervisor_pkg
from jarvis.supervisor import (
    Acceptor,
    AuthorityTier,
    BlobReader,
    Clock,
    EscalationReason,
    Evidence,
    EvidenceLedger,
    EvidencePrecedence,
    EvidenceSource,
    LifecycleDecision,
    LifecycleEvent,
    LifecycleState,
    LifecycleTransition,
    MutationGuard,
    MutationReport,
    Observer,
    PackageSnapshot,
    RecoveryAction,
    RecoveryPlan,
    RecoveryPolicy,
    Supervisor,
    SupervisorDecision,
    TaskLifecycle,
    VerificationResult,
    Verifier,
    decide_authority_tier,
    decide_recovery,
    is_creator_gated,
    lifecycle_decision,
)

AGGREGATOR = "jarvis.supervisor.supervisor"

# --- 1. the package facade -------------------------------------------------

EXPECTED_PUBLIC_API = [
    "Acceptor",
    "AuthorityTier",
    "BlobReader",
    "Clock",
    "EscalationReason",
    "Evidence",
    "EvidenceLedger",
    "EvidencePrecedence",
    "EvidenceSource",
    "LifecycleDecision",
    "LifecycleEvent",
    "LifecycleState",
    "LifecycleTransition",
    "MutationGuard",
    "MutationReport",
    "Observer",
    "PackageSnapshot",
    "RecoveryAction",
    "RecoveryPlan",
    "RecoveryPolicy",
    "Supervisor",
    "SupervisorDecision",
    "TaskLifecycle",
    "VerificationResult",
    "Verifier",
    "decide_authority_tier",
    "decide_recovery",
    "is_creator_gated",
    "lifecycle_decision",
    "lifecycle_transitions",
]


def test_package_all_is_exactly_the_declared_surface() -> None:
    assert sorted(supervisor_pkg.__all__) == EXPECTED_PUBLIC_API


def test_package_all_is_sorted_and_has_no_duplicates() -> None:
    assert list(supervisor_pkg.__all__) == sorted(supervisor_pkg.__all__)
    assert len(set(supervisor_pkg.__all__)) == len(supervisor_pkg.__all__)


def test_every_declared_export_resolves_on_the_package() -> None:
    unresolved = [n for n in EXPECTED_PUBLIC_API if not hasattr(supervisor_pkg, n)]
    assert unresolved == []


# --- 2. which module DEFINES each public name (the "home" map) --------------

NAME_HOME = {
    "AuthorityTier": "jarvis.supervisor.authority",
    "EscalationReason": "jarvis.supervisor.authority",
    "decide_authority_tier": "jarvis.supervisor.authority",
    "is_creator_gated": "jarvis.supervisor.authority",
    "Clock": "jarvis.supervisor.evidence",
    "Evidence": "jarvis.supervisor.evidence",
    "EvidenceLedger": "jarvis.supervisor.evidence",
    "EvidencePrecedence": "jarvis.supervisor.evidence",
    "EvidenceSource": "jarvis.supervisor.evidence",
    "VerificationResult": "jarvis.supervisor.evidence",
    "LifecycleDecision": "jarvis.supervisor.lifecycle",
    "LifecycleEvent": "jarvis.supervisor.lifecycle",
    "LifecycleState": "jarvis.supervisor.lifecycle",
    "LifecycleTransition": "jarvis.supervisor.lifecycle",
    "TaskLifecycle": "jarvis.supervisor.lifecycle",
    "lifecycle_decision": "jarvis.supervisor.lifecycle",
    "BlobReader": "jarvis.supervisor.mutation_guard",
    "MutationGuard": "jarvis.supervisor.mutation_guard",
    "MutationReport": "jarvis.supervisor.mutation_guard",
    "PackageSnapshot": "jarvis.supervisor.mutation_guard",
    "RecoveryAction": "jarvis.supervisor.recovery",
    "RecoveryPlan": "jarvis.supervisor.recovery",
    "RecoveryPolicy": "jarvis.supervisor.recovery",
    "decide_recovery": "jarvis.supervisor.recovery",
    "Supervisor": AGGREGATOR,
    "SupervisorDecision": AGGREGATOR,
    "Acceptor": AGGREGATOR,
    "Observer": AGGREGATOR,
    "Verifier": AGGREGATOR,
}


def test_each_public_name_is_defined_in_its_home_module() -> None:
    """The redirect that would have prevented the incident: read the home."""
    wrong = {}
    for name, home in NAME_HOME.items():
        module = importlib.import_module(home)
        actual = getattr(getattr(module, name), "__module__", None)
        if actual != home:
            wrong[name] = {"expected": home, "actual": actual}
    assert wrong == {}


def test_facade_exports_are_the_same_objects_as_their_home_definitions() -> None:
    for name in EXPECTED_PUBLIC_API:
        home = NAME_HOME.get(name)
        if home is None:
            # lifecycle_transitions is a module-level value, not a defined
            # class/function, so it carries no __module__ to pin.
            continue
        module = importlib.import_module(home)
        assert getattr(module, name) is getattr(supervisor_pkg, name), name


# --- 3. the submodule set --------------------------------------------------

EXPECTED_SUBMODULES = [
    "authority",
    "evidence",
    "lifecycle",
    "mutation_guard",
    "recovery",
    "supervisor",
]


def test_submodule_set_is_exactly_the_six_m2_5_modules() -> None:
    found = sorted(m.name for m in pkgutil.iter_modules(supervisor_pkg.__path__))
    assert found == EXPECTED_SUBMODULES


# --- 4. dataclass construction surface -------------------------------------

DATACLASS_FIELDS = [
    (Evidence, ["source", "precedence", "summary", "observed_at", "datum"]),
    (EvidenceLedger, ["observed_at", "entries"]),
    (VerificationResult, ["value", "source", "observed_at", "evidence"]),
    (LifecycleTransition, ["state", "event", "to", "creator_gated"]),
    (
        LifecycleDecision,
        ["current", "event", "next_state", "transition", "reason", "rejected"],
    ),
    (TaskLifecycle, ["state"]),
    (PackageSnapshot, ["blob_hashes", "sealed_at"]),
    (MutationReport, ["mutated", "added", "removed", "changed", "detail"]),
    (RecoveryPolicy, ["max_attempts", "rollback_available", "escalate_after"]),
    (
        RecoveryPlan,
        ["action", "reason", "attempts_used", "evidence", "creator_gated"],
    ),
    (
        SupervisorDecision,
        ["state", "verdict", "ledger", "verifier", "recovery", "reason", "mutation", "creator_gated"],
    ),
]


@pytest.mark.parametrize(
    ("datum", "expected"),
    DATACLASS_FIELDS,
    ids=[c.__name__ for c, _ in DATACLASS_FIELDS],
)
def test_dataclass_field_surface(datum: type, expected: list[str]) -> None:
    assert [f.name for f in fields(datum)] == expected


# --- 5. enum member sets (frozen decision data) ----------------------------

ENUM_MEMBERS = [
    (AuthorityTier, ["L0", "L1", "L2"]),
    (
        EscalationReason,
        [
            "FROZEN_CONFLICT",
            "SPEC_AMBIGUITY",
            "AUTHORITY_CHANGE",
            "IRREVERSIBLE",
            "MERGE_PUSH",
            "CONTEXT_DRIFT",
            "STALLED",
            "MUTATION_DETECTED",
            "RECOVERY_EXCEEDED",
        ],
    ),
    (
        EvidenceSource,
        [
            "FILESYSTEM",
            "FRESH_VERIFIER",
            "GIT_STATE",
            "IMMUTABLE_ARTIFACT",
            "TOOL_OUTPUT",
            "AGENT_INTERPRETATION",
            "AGENT_MEMORY",
        ],
    ),
    (
        EvidencePrecedence,
        [
            "FILESYSTEM",
            "FRESH_VERIFIER",
            "GIT_STATE",
            "IMMUTABLE_ARTIFACT",
            "TOOL_OUTPUT",
            "AGENT_INTERPRETATION",
            "AGENT_MEMORY",
        ],
    ),
    (
        LifecycleState,
        [
            "PROPOSED",
            "IMPLEMENTING",
            "WORKER_VERIFY",
            "PASS",
            "FROZEN_SUCCESS",
            "FAILED",
            "REPAIRING",
            "ESCALATED",
            "HELD",
        ],
    ),
    (
        LifecycleEvent,
        [
            "TASK_APPROVED",
            "EDIT_START",
            "WORKER_CLAIM_PASS",
            "INDEPENDENT_VERIFY_PASS",
            "INDEPENDENT_VERIFY_FAIL",
            "FREEZE",
            "MUTATION_DETECTED",
            "REPAIR_ATTEMPT",
            "RECOVERY_EXHAUSTED",
            "EPISTEMIC_CONFLICT",
            "STALLED",
            "CREATOR_ESCALATE",
            "CREATOR_RULING",
            "REOPEN",
        ],
    ),
    (RecoveryAction, ["NONE", "RETRY", "RESTART", "ROLLBACK", "ESCALATE", "HOLD"]),
]


@pytest.mark.parametrize(
    ("enum_cls", "expected"),
    ENUM_MEMBERS,
    ids=[c.__name__ for c, _ in ENUM_MEMBERS],
)
def test_enum_member_set(enum_cls: type[Enum], expected: list[str]) -> None:
    assert [m.name for m in enum_cls] == expected


def test_evidence_precedence_ranks_filesystem_top_and_agent_memory_bottom() -> None:
    """The rung ordering that the phantom ``FILESYSTEM_RUNG`` was groping for."""
    ordered = sorted(EvidencePrecedence, key=lambda p: p.value)
    assert ordered[-1] is EvidencePrecedence.FILESYSTEM
    assert ordered[0] is EvidencePrecedence.AGENT_MEMORY


# --- 6. public entry-point parameter shapes --------------------------------

_REQUIRED = "<required>"


def _shape(callable_obj: object) -> list[tuple[str, str, str]]:
    """(name, Parameter.kind, default) for each parameter of ``callable_obj``."""
    shape = []
    for param in inspect.signature(callable_obj).parameters.values():
        default = (
            _REQUIRED
            if param.default is inspect.Parameter.empty
            else repr(param.default)
        )
        shape.append((param.name, param.kind.name, default))
    return shape


POK = "POSITIONAL_OR_KEYWORD"
KWO = "KEYWORD_ONLY"

ENTRY_POINTS = [
    (decide_authority_tier, [("reason", POK, _REQUIRED)]),
    (is_creator_gated, [("reason", POK, _REQUIRED)]),
    (
        decide_recovery,
        [
            ("state", KWO, _REQUIRED),
            ("ledger", KWO, _REQUIRED),
            ("attempts_used", KWO, _REQUIRED),
            ("policy", KWO, _REQUIRED),
            ("reason", KWO, _REQUIRED),
        ],
    ),
    (lifecycle_decision, [("state", POK, _REQUIRED), ("event", POK, _REQUIRED)]),
    (Evidence.declare, [("source", POK, _REQUIRED), ("summary", POK, _REQUIRED), ("observed_at", POK, _REQUIRED)]),
    (EvidenceLedger.with_entry, [("self", POK, _REQUIRED), ("entry", POK, _REQUIRED)]),
    (EvidenceLedger.highest, [("self", POK, _REQUIRED)]),
    (EvidenceLedger.authority, [("self", POK, _REQUIRED)]),
    (EvidenceLedger.conflicts, [("self", POK, _REQUIRED), ("claimed", POK, _REQUIRED)]),
    (VerificationResult.decided, [("value", POK, _REQUIRED), ("source", POK, _REQUIRED), ("observed_at", POK, _REQUIRED), ("summary", POK, _REQUIRED)]),
    (PackageSnapshot.capture, [("relative_paths", POK, _REQUIRED), ("reader", POK, _REQUIRED), ("sealed_at", POK, _REQUIRED)]),
    (PackageSnapshot.folder_fingerprint, [("self", POK, _REQUIRED)]),
    (MutationGuard.seal, [("self", POK, _REQUIRED), ("snapshot", POK, _REQUIRED)]),
    (MutationGuard.check, [("self", POK, _REQUIRED), ("current", POK, _REQUIRED)]),
    (TaskLifecycle.apply, [("self", POK, _REQUIRED), ("event", POK, _REQUIRED)]),
    (
        TaskLifecycle.declared_transition,
        [("self", POK, _REQUIRED), ("event", POK, _REQUIRED), ("as_creator", KWO, _REQUIRED)],
    ),
    (Supervisor.decide, [("self", POK, _REQUIRED), ("worker_claim", KWO, _REQUIRED), ("observed_at", KWO, _REQUIRED)]),
    (
        Supervisor.verify,
        [
            ("self", POK, _REQUIRED),
            ("verifier", KWO, _REQUIRED),
            ("observed_at", KWO, _REQUIRED),
            ("repo_snapshot", KWO, "None"),
        ],
    ),
    (
        Supervisor.freeze,
        [("self", POK, _REQUIRED), ("observed_at", KWO, _REQUIRED), ("snapshot", KWO, _REQUIRED)],
    ),
    (Acceptor.accept, [("self", POK, _REQUIRED), ("decision", POK, _REQUIRED)]),
    (Observer.observe, [("self", POK, _REQUIRED)]),
    (Verifier.verify, [("self", POK, _REQUIRED)]),
    # --- the two injected DI seams (now facade exports) ---
    (Clock.now_iso, [("self", POK, _REQUIRED)]),
    (BlobReader.__call__, [("self", POK, _REQUIRED), ("relative_path", POK, _REQUIRED)]),
]


@pytest.mark.parametrize(
    ("callable_obj", "expected"),
    ENTRY_POINTS,
    ids=[getattr(c, "__qualname__", getattr(c, "__name__", repr(c))) for c, _ in ENTRY_POINTS],
)
def test_public_entry_point_parameter_shape(
    callable_obj: object, expected: list[tuple[str, str, str]]
) -> None:
    assert _shape(callable_obj) == expected


# --- 7. the incident negatives and the escalation that closed it ------------


def test_declare_is_a_factory_on_evidence_only() -> None:
    """``declare`` exists exactly once, on ``Evidence``."""
    assert hasattr(Evidence, "declare")
    assert callable(Evidence.declare)
    assert not hasattr(EvidenceLedger, "declare")
    assert not hasattr(PackageSnapshot, "declare")
    assert not hasattr(MutationGuard, "declare")


def test_names_hallucinated_in_the_2026_09_20_incident_do_not_exist() -> None:
    """Every binding below was written from memory and failed at runtime.

    If one of these is ever added deliberately, delete it from this test in the
    same commit - that is the point of pinning it.
    """
    assert not hasattr(EvidenceLedger, "FILESYSTEM_RUNG")
    assert not hasattr(EvidencePrecedence, "RUNG")
    assert not hasattr(Supervisor, "pure_fold")
    assert not hasattr(PackageSnapshot, "declare")


def test_aggregator_re_exports_all_four_authority_names_from_their_home() -> None:
    """The escalation: the aggregator previously re-exported three of the four
    authority names, and the missing one (``EscalationReason``) is exactly what
    made ``from jarvis.supervisor.supervisor import EscalationReason`` fail.
    Pin the identity so the omission cannot silently return.
    """
    aggregator = importlib.import_module(AGGREGATOR)
    authority = importlib.import_module("jarvis.supervisor.authority")
    for name in (
        "AuthorityTier",
        "EscalationReason",
        "decide_authority_tier",
        "is_creator_gated",
    ):
        assert getattr(aggregator, name) is getattr(authority, name), name


def test_aggregator_all_lists_only_its_own_definitions() -> None:
    """The aggregator's namespace carries re-exports by design; ``__all__`` is
    deliberately narrower - the five names ``supervisor.py`` DEFINES. Keep it
    that way so a star-import stays a contract, not a convenience dump.
    """
    aggregator = importlib.import_module(AGGREGATOR)
    assert sorted(aggregator.__all__) == [
        "Acceptor",
        "Observer",
        "Supervisor",
        "SupervisorDecision",
        "Verifier",
    ]


def test_facade_exposes_the_two_dependency_injection_seams() -> None:
    """``Clock`` and ``BlobReader`` are the only two ambient seams in the
    package. They must be importable from the facade, because implementing a
    hermetic clock or blob reader is the supported way to exercise the
    supervisor's opt-in adapters.
    """
    assert "Clock" in supervisor_pkg.__all__
    assert "BlobReader" in supervisor_pkg.__all__
    assert importlib.import_module("jarvis.supervisor.evidence").Clock is Clock
    assert importlib.import_module("jarvis.supervisor.mutation_guard").BlobReader is BlobReader
