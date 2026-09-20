from __future__ import annotations

"""Autonomous Engineering Supervisor - executable kernel (M2.5, spec 84.4).

The supervisor is the CONTROL surface that turns a single acceptance into a
RATCHET:

    observe -> decide -> act -> verify

Decisioning is DATA, not branches (84.4 precedent): the escalation ladder,
lifecycle transitions, and evidence precedence are declared by frozen policy
DATUM, never by code dispatch on identity. The worker must never be allowed
to verify its own success; this package splits the roles (implementer /
verifier) behind an explicit seam.

Hermetic default (kickoff item E / 84.4 precedent): on the SHIPPED default
policy the supervisor makes NO model calls, reads NO ambient state, performs
NO effects, and emits NO new event types. It decides through the SAME frozen
deterministic datums the M2.4 writer already gates with. Every rung that
could observe an external system is an OPT-IN adapter-backed seam (provider-
seam precedent) running ONLY when explicitly injected.

Determinism: same log + same policy -> identical result; clocks/randomness
are injected, never ambient; verification output is the AUTHORITY datum, never
a worker claim.

Additive law (M2.3 / M2.4 precedent, re-applied): this package is STRICTLY
additive. Nothing below lives in a frozen module; no frozen module is
import-modified or touched. New task, new ratchet, new package.
"""

from .authority import (
    AuthorityTier,
    EscalationReason,
    decide_authority_tier,
    is_creator_gated,
)
from .evidence import (
    Evidence,
    EvidenceLedger,
    EvidencePrecedence,
    EvidenceSource,
    VerificationResult,
)
from .lifecycle import (
    LifecycleEvent,
    LifecycleState,
    LifecycleTransition,
    TaskLifecycle,
    lifecycle_transitions,
)
from .mutation_guard import (
    MutationGuard,
    MutationReport,
    PackageSnapshot,
)
from .recovery import (
    RecoveryAction,
    RecoveryPlan,
    RecoveryPolicy,
    decide_recovery,
)
from .supervisor import (
    Acceptor,
    Observer,
    Supervisor,
    SupervisorDecision,
    Verifier,
)

__all__ = [
    "Acceptor",
    "AuthorityTier",
    "EscalationReason",
    "Evidence",
    "EvidenceLedger",
    "EvidencePrecedence",
    "EvidenceSource",
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
    "lifecycle_transitions",
]
