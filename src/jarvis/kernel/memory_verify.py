from __future__ import annotations

"""Memory verifier — ladder rungs 2-3 (M2.4, spec §84.4 / §127.1 / §112).

The §84.4 verification ladder is DATA-proportional to impact:

    cheap deterministic checks      (M2.1-M2.3, SHIPPED via the module-10
                                            writer gate)
            ↓
    semantic verifier               (this module)
            ↓
    independent verifier            (this module — HIGH-impact memories only)

M2.4 ships rungs 2-3 STRICTLY additively over the frozen M2.1-M2.3 write
path. Nothing about module 1-17 changes; `MemoryIndex`/`Memory.recall`
projection folds stay byte-identical on unchanged logs (the M2.3
fold-stability precedent, FB-M2.3-6 / F-M2.3-6, re-applied).

Hermetic default (kickoff item E / F-C9 precedent): on the SHIPPED default
`VerificationPolicy` the verifier makes NO model calls, reads NO ambient
state, performs NO effects, and emits NO new event types. It decides through
the SAME frozen deterministic gate the M2.3 writer already evaluates with
(`DoneGate`, kind "memory.write"). The semantic and independent rungs are
OPT-IN adapter-backed seams (§131.14 provider-seam precedent): they run ONLY
when an explicit policy supplies a provider — never from ambient state, never
auto-prompting.

Determinism: same log + same policy -> identical result; ULIDs/confidence/
validity are OUTCOME fields, never decision inputs. `verify()` is synchronous
and hermetic; `recall`/`retrieve`/`digest` semantics are untouched.

Decisioning is DATA, not branches (§84.4): the rung a given impact class
escalates to is declared by the `VerificationPolicy` ladder DATUM, never by
code dispatch on memory identity.
"""

from typing import Any, Callable, Literal, Mapping, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .done_gate import DoneGate, GateDecision
from .event_log import EventLog
from .memory_index import MemoryIndex
from .registry import CREATOR_PRINCIPAL_ID

MEMORY_STREAM_ID = "memory"

VerifierRung = Literal["cheap", "semantic", "independent"]
MemoryClass = Literal["episodic", "semantic", "procedural"]  # noqa: F401


class GateCheck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    passed: bool
    detail: str


class VerificationCheck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rung: VerifierRung
    name: str
    passed: bool
    detail: str


class VerificationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["verified", "held", "independent_failed"]
    reason: str | None = None
    rungs: tuple[VerifierRung, ...]
    checks: list[VerificationCheck]
    gate: GateDecision | None = None
    independent: dict[str, Any] | None = None
    mem_ids: list[str]


# ---------------------------------------------------------------------------
# Adapter seams for rungs 2-3 (§131.14 provider-seam precedent: OPT-IN, model
# backed, never ambient, never auto-prompt). Injection is explicit-policy-only.
# ---------------------------------------------------------------------------


class SemanticVerifier(Protocol):
    def verify(
        self, payload: Mapping[str, Any]
    ) -> tuple[bool, str]: ...


class IndependentVerifier(Protocol):
    def verify(
        self, payload: Mapping[str, Any]
    ) -> tuple[bool, str]: ...


# ---------------------------------------------------------------------------
# DATA: the verification ladder & impact gating (decisioning is data, not
# branches — kickoff item B / D, M2.3 DATA-policy precedent).
# ---------------------------------------------------------------------------


class HighImpactRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rungs: tuple[VerifierRung, ...] = ("semantic", "independent")
    impact_classes: tuple[MemoryClass, ...] = ("semantic", "procedural")
    independent_min_confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class SemanticRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    confidence_floor: float = Field(default=0.0, ge=0.0, le=1.0)
    require_evidence: bool = False


class VerificationPolicy(BaseModel):
    """Whole verification decision as DATA (kickoff item B).

    The default policy is the HERMETIC cheap rung — identical, in-kernel, to
    what the M2.3 writer already gates with. Rungs 2-3 are invoked ONLY when
    the caller injects an adapter-backed provider explicitly."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ladder: dict[MemoryClass, VerifierRung] = Field(
        default_factory=lambda: {
            "episodic": "cheap",
            "semantic": "semantic",
            "procedural": "semantic",
        }
    )
    high_impact: HighImpactRule = Field(default_factory=HighImpactRule)
    semantic: SemanticRule = Field(default_factory=SemanticRule)
    principal_id: str = CREATOR_PRINCIPAL_ID

    def rung_for(self, memory_class: MemoryClass) -> VerifierRung:
        return self.ladder.get(memory_class, "cheap")


class MemoryVerifier:
    """Deterministic verification seam (module 10 additive, §84.4).

    `verify()` re-derives the folded memory view (deterministic) and applies
    the ladder DATUM to each memory. The cheap rung is ALWAYS available and
    hermetic (the frozen writer gate). Rungs 2-3 are adapter-backed:
    `semantic_verifier`/`independent_verifier` run only when supplied, and
    only for impact classes the policy escalates; absent a provider the result
    carries `held` on that rung and never calls a model.
    """

    def __init__(
        self,
        log: EventLog,
        *,
        policy: VerificationPolicy | None = None,
        gate: DoneGate | None = None,
        semantic_verifier: SemanticVerifier | None = None,
        independent_verifier: IndependentVerifier | None = None,
    ) -> None:
        self._log = log
        self._policy = policy or VerificationPolicy()
        self._gate = gate or DoneGate()
        self._semantic = semantic_verifier
        self._independent = independent_verifier

    def verify(
        self,
        paths: list[str] | None = None,
        *,
        evidence: list[str] | None = None,
    ) -> VerificationResult:
        index = MemoryIndex.rebuild(self._log)
        mem_ids = list(index.memories) if paths is None else _resolve(paths, index)
        checks: list[VerificationCheck] = []
        rungs: tuple[VerifierRung, ...] = ("cheap",)
        independent_dump: dict[str, Any] | None = None
        held: list[str] = []

        for mem_id in mem_ids:
            payload = index.memories[mem_id]
            memory_class = payload.get("memory_class", "semantic")
            rung = self._policy.rung_for(memory_class)
            if "semantic" not in rungs:
                rungs = (rungs[0], rung) if rung != "cheap" else rungs

            cheap = self._gate.evaluate("memory.write", payload)
            checks.append(
                VerificationCheck(
                    rung="cheap",
                    name="deterministic",
                    passed=cheap.passed,
                    detail="frozen writer gate",
                )
            )
            if not cheap.passed:
                continue

            if rung in ("semantic", "independent") and self._semantic is not None:
                passed, detail = self._semantic.verify(payload)
                checks.append(
                    VerificationCheck(
                        rung="semantic", name="semantic", passed=passed, detail=detail
                    )
                )
                if not passed:
                    continue
            elif rung in ("semantic", "independent") and "semantic" not in [
                c.name for c in checks
            ]:
                checks.append(
                    VerificationCheck(
                        rung=rung,
                        name="semantic",
                        passed=False,
                        detail="semantic_verifier not configured (hermetic hold)",
                    )
                )
                held.append(mem_id)
                continue

            if rung == "independent":
                if self._independent is None:
                    independent_dump = {
                        "status": "held",
                        "detail": "independent_verifier not configured (hermetic hold)",
                    }
                    held.append(mem_id)
                    continue
                passed, detail = self._independent.verify(payload)
                checks.append(
                    VerificationCheck(
                        rung="independent",
                        name="independent",
                        passed=passed,
                        detail=detail,
                    )
                )
                independent_dump = {"status": "passed" if passed else "failed", "detail": detail}
                if not passed:
                    return VerificationResult(
                        status="independent_failed",
                        reason=f"independent verification failed for {mem_id}",
                        rungs=rungs,
                        checks=checks,
                        gate=cheap,
                        independent=independent_dump,
                        mem_ids=mem_ids,
                    )

        status: Literal["verified", "held"] = "verified" if not held else "held"
        return VerificationResult(
            status=status,
            reason=f"held rungs: {', '.join(held)}" if held else None,
            rungs=rungs,
            checks=checks,
            gate=None,
            independent=independent_dump,
            mem_ids=mem_ids,
        )


def _resolve(paths: list[str], index: MemoryIndex) -> list[str]:
    resolved: list[str] = []
    for path in paths:
        if path in index.memories:
            resolved.append(path)
    return resolved
