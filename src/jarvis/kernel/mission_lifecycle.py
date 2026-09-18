from __future__ import annotations

"""Deterministic mission-lifecycle FSM (module 14, STRETCH M1.1, spec §134.1).

The full mission-lifecycle FSM is STRETCH (M1.1) per §134.1; the M1 MUST
slice delivered only the deterministic done gate (module 10) and the
single-effect envelope (module 8). Module 14 closes the gap with the
lifecycle schema an M2/M3 orchestrator needs while keeping the kernel
deterministic:

    pending  --mission.started-->  executing
    executing --task.completed-->  completed
    executing --task.completion_refused-->  refused
    {pending,executing} --effect.failed-->  compensated

Model: a pure fold over appended events, on the MemoryProjection (module 7)
precedent. The machine

- evaluates PURELY on events already in the log (`rebuild`/`advance` fold the
  integrity-verified replay slice; step has no hidden now()/RNG/network);
- emits `lifecycle.*` audit events on stream "mission" ONLY when a transition
  fires, and appends one only if the same (transition, cause) is not already
  recorded — so a second `advance()` after a restart appends nothing
  (idempotent);
- never treats `lifecycle.*` as intake (no transition-table cells), so the
  append -> fold -> append loop cannot run;
- NEVER appends `task.completed` — that emission belongs exclusively to
  `CompletionGate` (module 10, NAT-05); this module consumes it;
- threads its `observer` into every `EffectEnvelopeEngine` it constructs
  (F-E15 residual), so effect/verify spans finally have a caller.

Contract refinement (docs/MODULE14_IMPLEMENTATION.md): the kickoff named
`intent.accepted` (module 3) as intake, but module 3 emits no events
(`validate_proposal` returns synchronously). Module 14 therefore defines its
own `mission.started` intake on the mission stream as the
`pending -> executing` trigger; nothing else changes.

Determinism G20/NAT-03: `rebuild` twice over an identical log yields
identical state and digest. Cross-run digests are NOT promised (payloads
carry wall-clock timestamps). The digest is sha256 over canonical state
(excluding event bytes/timestamps), mirroring `MemoryProjection.digest()`.

Judgment call (documented): `effect.refused` (NAT-01 style) folds into the
effect ledger but does NOT terminate a mission — a sub-effect authorization
refusal is not a mission refusal; the orchestrator's later gated/un-gated
completion drives `refused`. Terminal states are absorbing: once
completed/refused/compensated, later events are ignored.
"""

from hashlib import sha256
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict

from .done_gate import COMPLETION_REFUSED_EVENT_TYPE, COMPLETION_EVENT_TYPE
from .effect_envelope import EffectEnvelopeEngine
from .event_log import Clock, Event, EventLog, _canonical_json
from .registry import CREATOR_PRINCIPAL_ID

LifecycleState: TypeAlias = Literal[
    "pending", "executing", "completed", "refused", "compensated"
]

MISSION_STREAM_ID = "mission"
MISSION_STARTED = "mission.started"

LIFECYCLE_ACCEPTED = "lifecycle.accepted"
LIFECYCLE_COMPLETED = "lifecycle.completed"
LIFECYCLE_REFUSED = "lifecycle.refused"
LIFECYCLE_COMPENSATED = "lifecycle.compensated"

EFFECT_PREPARED = "effect.prepared"
EFFECT_AUTHORIZED = "effect.authorized"
EFFECT_COMMITTED = "effect.committed"
EFFECT_VERIFIED = "effect.verified"
EFFECT_REFUSED = "effect.refused"
EFFECT_FAILED = "effect.failed"

_LIFECYCLE_EVENT_TYPES = frozenset(
    {
        LIFECYCLE_ACCEPTED,
        LIFECYCLE_COMPLETED,
        LIFECYCLE_REFUSED,
        LIFECYCLE_COMPENSATED,
    }
)

_INTAKE_EVENT_TYPES = frozenset(
    {
        MISSION_STARTED,
        COMPLETION_EVENT_TYPE,
        COMPLETION_REFUSED_EVENT_TYPE,
        EFFECT_PREPARED,
        EFFECT_AUTHORIZED,
        EFFECT_COMMITTED,
        EFFECT_VERIFIED,
        EFFECT_REFUSED,
        EFFECT_FAILED,
    }
)

TERMINAL_STATES: frozenset[LifecycleState] = frozenset(
    {"completed", "refused", "compensated"}
)

# The DATA transition table: (state, event_type) -> next state.
TRANSITIONS: dict[tuple[LifecycleState, str], LifecycleState] = {
    ("pending", MISSION_STARTED): "executing",
    ("executing", COMPLETION_EVENT_TYPE): "completed",
    ("executing", COMPLETION_REFUSED_EVENT_TYPE): "refused",
    ("pending", EFFECT_FAILED): "compensated",
    ("executing", EFFECT_FAILED): "compensated",
}

# lifecycle.* audit event emitted when entering a target state.
LIFECYCLE_EVENT_BY_STATE: dict[LifecycleState, str] = {
    "executing": LIFECYCLE_ACCEPTED,
    "completed": LIFECYCLE_COMPLETED,
    "refused": LIFECYCLE_REFUSED,
    "compensated": LIFECYCLE_COMPENSATED,
}


class EffectRecord(BaseModel):
    """Latest observed phase of one effect folded into the mission slice."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    effect_id: str
    phase: str


class CompensationRecord(BaseModel):
    """Declared compensation need for a FAILED effect (§83).

    M1.1 declares the seam: `status` starts at "declared" and the real
    compensator adapters/execution land with M2 effects. Compensation never
    erases history — it creates new corrective events (§83).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    effect_id: str
    failed_event_id: str
    intended_change: dict[str, Any]
    status: Literal["declared", "pending", "executed"] = "declared"


class MissionLifecycle(BaseModel):
    """Frozen mission-lifecycle state (deterministic fold result)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str
    state: LifecycleState = "pending"
    event_count: int = 0
    effects: tuple[EffectRecord, ...] = ()
    compensation: tuple[CompensationRecord, ...] = ()

    @classmethod
    def initial(cls, mission_id: str) -> "MissionLifecycle":
        return cls(mission_id=mission_id)

    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def step(self, event: Event) -> tuple["MissionLifecycle", Event | None]:
        """Pure fold step over one appended event.

        Returns (next lifecycle, optional `lifecycle.*` event to append).
        No side effects, no clock, no RNG. `lifecycle.*` events and events
        for other missions are no-ops.
        """
        if event.mission_id != self.mission_id:
            return self, None
        if event.event_type in _LIFECYCLE_EVENT_TYPES:
            return self, None
        if self.is_terminal():
            # absorbing: a finished mission ignores later events entirely —
            # no transition, no ledger update, no event_count advance.
            return self, None

        effects = self.effects
        effect_id = event.payload.get("effect_id") if event.payload else None
        if isinstance(effect_id, str) and effect_id:
            effects = tuple(
                (EffectRecord(effect_id=effect_id, phase=event.event_type))
                if record.effect_id == effect_id
                else record
                for record in self.effects
            )
            if not any(record.effect_id == effect_id for record in self.effects):
                effects = effects + (
                    EffectRecord(effect_id=effect_id, phase=event.event_type),
                )

        compensation = self.compensation
        if event.event_type == EFFECT_FAILED and isinstance(effect_id, str) and effect_id:
            compensation = compensation + (
                CompensationRecord(
                    effect_id=effect_id,
                    failed_event_id=event.event_id or "",
                    intended_change=dict(
                        event.payload.get("intended_change") or {}
                    ),
                ),
            )

        emitted: Event | None = None
        state: LifecycleState = self.state
        if not self.is_terminal():
            target = TRANSITIONS.get((self.state, event.event_type))
            if target is not None:
                state = target
                emitted = Event(
                    stream_id=MISSION_STREAM_ID,
                    event_type=LIFECYCLE_EVENT_BY_STATE[target],
                    principal_id=event.principal_id,
                    mission_id=self.mission_id,
                    cause_event_id=event.event_id,
                    correlation_id=self.mission_id,
                    payload={
                        "from": self.state,
                        "to": target,
                        "intake_event_type": event.event_type,
                        "cause_event_id": event.event_id,
                    },
                )

        return (
            self.model_copy(
                update={
                    "state": state,
                    "event_count": self.event_count + 1,
                    "effects": effects,
                    "compensation": compensation,
                }
            ),
            emitted,
        )

    def digest(self) -> str:
        """Deterministic digest over canonical lifecycle STATE.

        Identical logs -> identical digest (G20/NAT-03). Cross-run equality
        is NOT promised because some folded payloads carry wall-clock
        timestamps. Mirrors `MemoryProjection.digest()`.
        """
        return sha256(_canonical_json(self.model_dump())).hexdigest()

    def effect_ids(self) -> list[str]:
        return [record.effect_id for record in self.effects]


class MissionLifecycleOwner:
    """Per-mission FSM owner watched over the "mission" stream.

    `advance()` is the tail-following reader: it folds the mission's slice
    of the log and appends any missing `lifecycle.*` transition events. It
    is idempotent — re-advancing over an unchanged log appends nothing.
    """

    def __init__(
        self,
        log: EventLog,
        *,
        mission_id: str,
        observer: Any | None = None,
        principal_id: str = CREATOR_PRINCIPAL_ID,
    ) -> None:
        self._log = log
        self._mission_id = mission_id
        self._observer = observer
        self._principal_id = principal_id

    # ---- fold ------------------------------------------------------------

    def _slice(self) -> list[Event]:
        return [
            event
            for event in self._log.replay()
            if event.mission_id == self._mission_id
            and (
                event.event_type in _INTAKE_EVENT_TYPES
                or event.event_type in _LIFECYCLE_EVENT_TYPES
            )
        ]

    def rebuild(self) -> MissionLifecycle:
        """Read-only fold: no writes. Handles `EventLog` as the source of
        truth, delegating integrity checking to `replay()` (NAT-04)."""
        state = MissionLifecycle.initial(self._mission_id)
        for event in self._slice():
            state, _ = state.step(event)
        return state

    def advance(self) -> tuple[MissionLifecycle, list[str]]:
        """Fold the slice and append any missing lifecycle events.

        Appending is skipped when a `lifecycle.*` event with the same
        (transition, cause_event_id) already exists, so a second advance
        over an unchanged log appends nothing (loop-safe, idempotent).
        """
        slice_events = self._slice()
        existing_causes = {
            event.cause_event_id
            for event in slice_events
            if event.event_type in _LIFECYCLE_EVENT_TYPES
        }

        state = MissionLifecycle.initial(self._mission_id)
        appended: list[str] = []
        for event in slice_events:
            state, emitted = state.step(event)
            if emitted is not None and emitted.cause_event_id not in existing_causes:
                event_id = self._log.append(emitted)
                appended.append(event_id)
                existing_causes.add(emitted.cause_event_id)
        return state, appended

    # ---- effect engine construction (F-E15) ------------------------------

    def build_effect_engine(
        self,
        resolver: Any,
        adapters: dict[str, Any],
        *,
        principal_id: str | None = None,
        clock: Clock | None = None,
    ) -> EffectEnvelopeEngine:
        """Build an `EffectEnvelopeEngine` with this owner's observer ALWAYS
        threaded (F-E15 residual: effect/verify spans get a caller). No
        observer -> NoOp, unchanged effect behavior."""
        return EffectEnvelopeEngine(
            resolver,
            adapters,
            log=self._log,
            principal_id=principal_id or self._principal_id,
            observer=self._observer,
            clock=clock,
        )