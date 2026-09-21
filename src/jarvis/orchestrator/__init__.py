from __future__ import annotations

"""Autonomous Engineering Orchestrator - the multi-mission execution plane
(M3.2 / M3.3, spec 84.4 determinism, re-applied).

The orchestrator is where DECLARED plans get folded into accepted datums. It
adds NO new authority and NO new state machine: per step it drives the SAME
frozen supervisor TaskLifecycle ratchet and consults the SAME recovery ladder,
with the SAME evidence hierarchy. `scripts/verify.py` (the L0 Verification
Authority) is the step verifier seam; it is NEVER the worker, and a worker
claim can never set a true value.

Bridges (L7) and Router (L5) connect untrusted LLM workers while enforcing
strict role isolation and Invariant I5 (Red-team != Verifier).

Additive law (M2.3/M2.4/M2.5 precedent, re-applied): this package is STRICTLY
additive. Nothing below lives in a frozen module; no frozen module is
import-modified or touched. New mission, new package.
"""

from .bridges import (
    AgyBridge,
    Artifacts,
    Bridge,
    CommandRunner,
    DeepSeekBridge,
    Handle,
    OpenCodeBridge,
    Sandbox,
    WorkerStatus,
)
from .mission_runner import (
    Decomposer,
    MissionPlan,
    MissionRun,
    MissionRunner,
    MissionStep,
    MissionStepResult,
    StepVerifier,
)
from .router import (
    Capability,
    ProviderProfile,
    Role,
    RoleAssignment,
    Router,
    RouterResult,
    default_provider_registry,
)

__all__ = [
    "AgyBridge",
    "Artifacts",
    "Bridge",
    "Capability",
    "CommandRunner",
    "Decomposer",
    "DeepSeekBridge",
    "Handle",
    "MissionPlan",
    "MissionRun",
    "MissionRunner",
    "MissionStep",
    "MissionStepResult",
    "OpenCodeBridge",
    "ProviderProfile",
    "Role",
    "RoleAssignment",
    "Router",
    "RouterResult",
    "Sandbox",
    "StepVerifier",
    "WorkerStatus",
    "default_provider_registry",
]