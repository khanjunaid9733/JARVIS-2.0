from __future__ import annotations

"""Deterministic completion gate (module 10, spec §81.3 / §98 / §112 / NAT-05).

> "The model builds. The deterministic gate decides done." (§81.3)

The gate is a pure function over an explicit evidence mapping: given a
`kind` and the evidence, it runs a fixed, data-driven list of deterministic
predicates and returns a frozen `GateDecision`. It never calls a model,
never performs an effect, and holds no ambient state (§79/§80.3).

NAT-05 (§134.3): an agent cannot self-declare completion. Completion is only
ever emitted through `CompletionGate.declare_completion`, which first
requires a PASSING gate decision; a failed decision appends a
`task.completion_refused` audit event and never a completion event.

Scope note: the FULL mission-lifecycle FSM is STRETCH (M1.1) per §134.1; this
module implements only the deterministic completion gate the M1 MUST slice
needs for NAT-05. Evidence *shape* per kind is a disclosed M1 default — the
spec fixes that completion requires objective evidence (§81.3), not the
exact predicate set.
"""

from collections.abc import Callable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

from .event_log import Event, EventLog

COMPLETION_STREAM_ID = "orchestration"
COMPLETION_EVENT_TYPE = "task.completed"
COMPLETION_REFUSED_EVENT_TYPE = "task.completion_refused"


class GateCheck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    passed: bool
    detail: str


class GateDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    passed: bool
    checks: list[GateCheck]

    def check(self, name: str) -> bool:
        for check in self.checks:
            if check.name == name:
                return check.passed
        raise KeyError(name)


# ---------------------------------------------------------------------------
# Deterministic predicates and requirements (data, not branching)
# ---------------------------------------------------------------------------

CheckFn = Callable[[Mapping[str, Any]], "tuple[bool, str]"]


def _nonempty(evidence: Mapping[str, Any], key: str) -> tuple[bool, str]:
    value = evidence.get(key)
    ok = isinstance(value, str) and value.strip() != ""
    return ok, f"{key}={'present' if ok else 'missing-or-empty'}"


def _confidence_valid(evidence: Mapping[str, Any]) -> tuple[bool, str]:
    value = evidence.get("confidence")
    ok = (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0.0 <= float(value) <= 1.0
    )
    return ok, f"confidence={value!r} {'ok' if ok else 'outside [0,1]'}"


def _artifact_present(evidence: Mapping[str, Any]) -> tuple[bool, str]:
    value = evidence.get("artifact")
    ok = value is not None and value != "" and value != {} and value != []
    return ok, f"artifact={'present' if ok else 'missing'}"


CHECKS: dict[str, CheckFn] = {
    "content_present": lambda e: _nonempty(e, "content"),
    "source_present": lambda e: _nonempty(e, "source"),
    "confidence_valid": _confidence_valid,
    "artifact_present": _artifact_present,
    "verification_present": lambda e: _nonempty(e, "verification"),
}

# kind -> required check names, in deterministic order.
GATE_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "memory.write": ("content_present", "source_present", "confidence_valid"),
    "task.completion": ("artifact_present", "verification_present"),
}


class DoneGate:
    """Evaluates a registered gate kind against explicit evidence."""

    @staticmethod
    def requirements(kind: str) -> tuple[str, ...]:
        try:
            return GATE_REQUIREMENTS[kind]
        except KeyError as exc:
            raise KeyError(f"no gate requirements registered for kind {kind!r}") from exc

    def evaluate(self, kind: str, evidence: Mapping[str, Any]) -> GateDecision:
        checks: list[GateCheck] = []
        for name in self.requirements(kind):
            passed, detail = CHECKS[name](evidence)
            checks.append(GateCheck(name=name, passed=passed, detail=detail))
        return GateDecision(
            kind=kind,
            passed=all(check.passed for check in checks),
            checks=checks,
        )


class CompletionGate:
    """The only path that may emit a completion event (NAT-05).

    A completion is emitted iff the deterministic `task.completion` gate
    passes; otherwise a `task.completion_refused` audit event is appended and
    no completion event exists.
    """

    def __init__(
        self,
        log: EventLog,
        *,
        gate: DoneGate | None = None,
        principal_id: str,
    ) -> None:
        self._log = log
        self._gate = gate or DoneGate()
        self._principal_id = principal_id

    def declare_completion(
        self,
        *,
        task_id: str,
        evidence: Mapping[str, Any],
        mission_id: str | None = None,
    ) -> GateDecision:
        decision = self._gate.evaluate("task.completion", evidence)
        self._emit(
            decision,
            task_id=task_id,
            mission_id=mission_id,
            evidence=evidence,
        )
        return decision

    def _emit(
        self,
        decision: GateDecision,
        *,
        task_id: str,
        mission_id: str | None,
        evidence: Mapping[str, Any],
    ) -> None:
        event_type = (
            COMPLETION_EVENT_TYPE if decision.passed else COMPLETION_REFUSED_EVENT_TYPE
        )
        self._log.append(
            Event(
                stream_id=COMPLETION_STREAM_ID,
                event_type=event_type,
                principal_id=self._principal_id,
                mission_id=mission_id,
                task_id=task_id,
                payload={
                    "kind": decision.kind,
                    "passed": decision.passed,
                    "checks": [check.model_dump() for check in decision.checks],
                    "evidence": dict(evidence),
                },
            )
        )
