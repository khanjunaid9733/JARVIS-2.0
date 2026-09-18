from __future__ import annotations

"""Full `jarvis explain` cause-chain rendering (module 17, STRETCH M1.1, §134.1).

The §127.1 transcript shows an `explain` that renders the cause chain, the
state transitions, model provenance, retrieved memories, capability checks,
effect confinement, and the budget line. Module 11/CLI ships the minimal
version (chain + event metadata); M1.1 closes the gap with a pure, read-only
renderer over the integrity-verified log:

- cause chain walking (`cause_event_id` edges, root-first display order)
- mission-lifecycle state + transitions when the target participates in a
  mission stream (fold via `MissionLifecycleOwner.rebuild`, module 14)
- retrieved-memory provenance + scores for `question.asked` targets
  (`recall`, module 11)
- `policy.check` capability checks and `effect.*` confinement counted over
  the chain (none today on the offline path)
- budget accounting slab for the target's stream (`BudgetLedger`, module 16)

The renderer writes nothing and never calls a model; it is a deterministic
function of the log (G20/NAT-03 — identical logs, identical explanations).
The CLI formats the structure; this module owns the semantics.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict

from .budget_ledger import BudgetLedger, StreamBudget
from .event_log import Event, EventLog
from .memory_projection import MemoryProjection
from .memory_query import RecalledMemory, recall
from .memory_write import MEMORY_COMMITTED
from .mission_lifecycle import LIFECYCLE_EVENT_BY_STATE, MissionLifecycleOwner
from .model_answer import QUESTION_ASKED
from .policy import POLICY_EVENT_TYPE


class ChainLink(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    event_type: str
    cause_event_id: str | None


class Explanation(BaseModel):
    """Structured, renderable explanation of one event (read-only fold)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_event_id: str
    event_type: str
    principal_id: str
    stream_id: str
    chain: list[ChainLink]
    lifecycle_state: str | None = None
    lifecycle_transitions: list[str] = ()
    model_provenance: dict[str, Any] | None = None
    recalled_memories: list[RecalledMemory] = ()
    memory_content: str | None = None
    memory_source: str | None = None
    capability_check_count: int = 0
    effect_count: int = 0
    budget: StreamBudget | None = None


def explain_event(
    log: EventLog,
    projection: MemoryProjection,
    event_id: str,
    *,
    recall_limit: int = 3,
) -> Explanation | None:
    """Build the Explanation for `event_id`, or None when unknown."""
    events = log.replay()
    by_id = {event.event_id: event for event in events}
    target = by_id.get(event_id)
    if target is None:
        return None

    chain: list[ChainLink] = []
    current: Event | None = target
    root_chain: list[Event] = []
    while current is not None:
        root_chain.append(current)
        current = by_id.get(current.cause_event_id) if current.cause_event_id else None
    chain = [
        ChainLink(event_id=event.event_id or "?", event_type=event.event_type, cause_event_id=event.cause_event_id)
        for event in root_chain
    ]

    lifecycle_state: str | None = None
    transitions: list[str] = []
    mission_id = target.mission_id
    if mission_id:
        lifecycle = MissionLifecycleOwner(log, mission_id=mission_id).rebuild()
        lifecycle_state = lifecycle.state
        lifecycle_names = set(LIFECYCLE_EVENT_BY_STATE.values())
        transitions = [
            event.event_type
            for event in events
            if event.mission_id == mission_id
            and event.event_type in lifecycle_names
        ]

    model_provenance: dict[str, Any] | None = None
    recalled_memories: list[RecalledMemory] = []
    if target.event_type == QUESTION_ASKED:
        payload = dict(target.payload or {})
        question = str(payload.get("question", ""))
        model_provenance = payload
        if question:
            recalled_memories = recall(
                projection, question, limit=max(recall_limit, 1)
            )

    memory_content: str | None = None
    memory_source: str | None = None
    if target.event_type == MEMORY_COMMITTED:
        payload = target.payload or {}
        raw_content = payload.get("content")
        raw_source = payload.get("source")
        memory_content = str(raw_content) if raw_content is not None else None
        memory_source = str(raw_source) if raw_source is not None else None

    # Policy checks and effects are counted over the target's mission slice
    # (when it belongs to a mission) or over its own cause chain, so a
    # mission's related audit events are observable together.
    related = [
        event
        for event in events
        if (mission_id and event.mission_id == mission_id)
        or (
            not mission_id
            and event.event_id in {link.event_id for link in chain}
        )
    ]
    capability_checks = sum(
        1 for event in related if event.event_type == POLICY_EVENT_TYPE
    )
    effect_ids = {
        str(event.payload.get("effect_id"))
        for event in related
        if event.event_type.startswith("effect.")
        and event.payload.get("effect_id") is not None
    }
    effect_count = len(effect_ids)

    budget = BudgetLedger.rebuild(events).stream_budget(
        target.mission_id or target.stream_id or "session"
    )

    return Explanation(
        target_event_id=event_id,
        event_type=target.event_type,
        principal_id=target.principal_id,
        stream_id=target.stream_id,
        chain=chain,
        lifecycle_state=lifecycle_state,
        lifecycle_transitions=transitions,
        model_provenance=model_provenance,
        recalled_memories=recalled_memories,
        memory_content=memory_content,
        memory_source=memory_source,
        capability_check_count=capability_checks,
        effect_count=effect_count,
        budget=budget,
    )