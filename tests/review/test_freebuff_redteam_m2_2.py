from __future__ import annotations

"""Freebuff M2.2 red-team evidence probes — branch `task/m2.2` @ `8f788c5`.

These are EVIDENCE, not accepted architecture (Freebuff role contract). Each
test PINS the behavior observed on disk and names, in a comment, the behavior
the finding recommends. Assertions marked ``# FLIPS ON FIX`` are the ones that
change when (and only when) the corresponding fix lands; the rest are
regression pins for behavior the red-team considers acceptable or contract-
compliant today.

Targets: src/jarvis/kernel/memory_retrieval.py, model_gateway.py (additive
`role_contracts` kwarg), memory_api.py (`Memory.retrieve`), the
`memory.retrieve.reranked` audit event.

Findings report: docs/M2_2_REDTEAM_FB.md
"""

import math

import pytest

from jarvis.kernel.event_log import Event, EventLog
from jarvis.kernel.memory_api import Memory
from jarvis.kernel.memory_index import MemoryIndex
from jarvis.kernel.memory_projection import MemoryProjection
from jarvis.kernel.memory_query import recall as module11_recall
from jarvis.kernel.memory_retrieval import (
    M2_ROLE_CONTRACTS,
    MEMORY_RETRIEVE_RERANKED,
    ModelRetrievalRanker,
    RankedMemory,
    RerankScores,
    retrieve,
)
from jarvis.kernel.memory_trace import MemoryTraceWriter
from jarvis.kernel.memory_write import MemoryWriter
from jarvis.kernel.model_gateway import (
    M1_ROLE_CONTRACTS,
    ModelGateway,
    ProviderTransportError,
    RoleContract,
    TypedFailure,
    ValidatedOutput,
)
from jarvis.kernel.registry import (
    CREATOR_PRINCIPAL_ID,
    CapabilityRegistry,
    ContractDef,
    ProviderBinding,
    ProviderMeta,
)

pytestmark = pytest.mark.anyio


class _FixedClock:
    def now_utc_iso(self) -> str:
        return "2026-09-18T00:00:00.000Z"


def _log(tmp_path, name: str = "log.db") -> EventLog:
    return EventLog(db_path=str(tmp_path / name), clock=_FixedClock())


class _DrainAdapter:
    """One output per call; empty queue returns {} (validation junk)."""

    provider_id = "model.adapter"

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    async def invoke(self, contract_id, version, args):
        self.calls += 1
        if not self.outputs:
            return {}
        return self.outputs.pop(0)

    def health_check(self):
        return True


class _BombAdapter:
    """Raise or count on any invoke — must never be dialled offline."""

    provider_id = "model.adapter"

    def __init__(self):
        self.calls = 0

    async def invoke(self, contract_id, version, args):
        self.calls += 1
        return {}

    def health_check(self):
        return True


class _RepeatAdapter:
    """Repeats the SAME output for every call (multi-call determinism probes)."""

    provider_id = "model.adapter"

    def __init__(self, output):
        self.output = output
        self.calls = 0

    async def invoke(self, contract_id, version, args):
        self.calls += 1
        return self.output

    def health_check(self):
        return True


class _RaiseAdapter:
    provider_id = "model.adapter"

    def __init__(self, exc):
        self.exc = exc
        self.calls = 0

    async def invoke(self, contract_id, version, args):
        self.calls += 1
        raise self.exc

    def health_check(self):
        return True


def _rerank_binding(provider_id: str = "model.adapter") -> ProviderBinding:
    return ProviderBinding(
        meta=ProviderMeta(
            provider_id=provider_id,
            version="1.0.0",
            license="MIT",
            license_compatibility="approved",
            adapter="jarvis.providers.rerank.test",
            trust_level="trusted",
            process_model="in_process",
            network="egress_only",
            health_check="probe",
            cve_status="checked_clean",
            provenance_added_by="creator",
            provenance_added_at_utc="2026-09-18T00:00:00Z",
            provenance_reason="M2.2 rerank seam red-team probe",
            fallback_provider_id=None,
        ),
        contracts=[
            ContractDef(
                contract_id="memory.rerank",
                version="1.0.0",
                args_schema={"query": {"type": "string", "required": True}},
            )
        ],
    )


async def _seed(log: EventLog) -> None:
    MemoryWriter(log).remember(content="umbrella is a company", source="s")
    MemoryTraceWriter(log).record_episodic(
        content="safe word umbrella", source="agent.run"
    )


def _ranked(gateway: ModelGateway) -> ModelRetrievalRanker:
    return ModelRetrievalRanker(gateway)


def _gateway_with(adapter, registry=None) -> tuple[ModelGateway, CapabilityRegistry]:
    reg = registry or CapabilityRegistry()
    if not isinstance(reg, CapabilityRegistry) or not reg.get_provider("model.adapter"):
        pass
    return ModelGateway(resolver=reg, adapters={"model.adapter": adapter}), reg


# ---------------------------------------------------------------------------
# A. Hermeticity + offline determinism (PASS pins)
# ---------------------------------------------------------------------------

async def test_a1_offline_noop_retrieve_mutates_nothing_and_generates_no_ids(tmp_path):
    """A1 — Hermeticity: ranker=None path appends NOTHING to the log and
    generates no new ULID / no clock read (replay is byte-identical, and the
    audit semantics hold that no model ran)."""
    log = _log(tmp_path)
    await _seed(log)
    before = [(e.event_id, e.stream_seq, e.payload_sha256, e.event_sha256)
              for e in log.replay()]

    hits = await Memory(log=log).retrieve("umbrella", limit=3)

    after = [(e.event_id, e.stream_seq, e.payload_sha256, e.event_sha256)
             for e in log.replay()]
    assert before == after
    assert log.replay() == log.replay()
    assert [e.event_type for e in log.replay()] == [
        "memory.write.proposed",
        "memory.write.verified",
        "memory.write.committed",
        "memory.trace.recorded",
    ]
    assert len(hits) == 2


async def test_a2_offline_deterministic_twice_and_across_fresh_rebuild(tmp_path):
    """A2 — Determinism: same log + ranker=None twice and after a rebuild from
    the same db yields byte-identical RankedMemory output (mirrors NAT-03)."""
    log = _log(tmp_path)
    await _seed(log)
    log.append(Event(stream_id="memory", event_type="noise.other",
                     principal_id=CREATOR_PRINCIPAL_ID, payload={"x": 1}))

    first = await Memory(log=log).retrieve("umbrella tool", limit=3)
    second = await Memory(index=MemoryIndex.rebuild(log)).retrieve("umbrella tool", limit=3)

    assert [h.model_dump() for h in first] == [h.model_dump() for h in second]

    log.close()
    reopened = EventLog(db_path=str(tmp_path / "log.db"), clock=_FixedClock())
    third = await Memory(log=reopened).retrieve("umbrella tool", limit=3)
    assert [h.model_dump() for h in first] == [h.model_dump() for h in third]


async def test_a3_module11_byte_parity_on_no_trace_log(tmp_path):
    """A3 — For a memory-only log, retrieve() output is byte-content/order/score
    identical to the frozen module-11 recall() (the M2.1 parity promise)."""
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="the capital of France is Paris", source="s")
    MemoryWriter(log).remember(content="umbrella is a company", source="handbook")
    proj = MemoryProjection.rebuild(log)

    expected = module11_recall(proj, "what is the capital of France?", limit=3)
    got = await Memory(projection=proj).retrieve("what is the capital of France?", limit=3)

    assert [(h.content, h.score) for h in got] == [(h.content, h.score) for h in expected]
    assert [h.tier for h in got] == ["memory"] * len(got)
    assert all(h.verified is True for h in got)


async def test_a4_no_rerank_provider_never_dials_remote_and_no_audit(tmp_path):
    """A4 — Bogus backend never dialled: a registry with NO memory.rerank
    binding falls back to lexical order, calls nothing, audits nothing."""
    log = _log(tmp_path)
    await _seed(log)
    bomb = _BombAdapter()
    gateway, _ = _gateway_with(bomb, CapabilityRegistry.seed_m1_defaults())

    hits = await Memory(log=log).retrieve(
        "umbrella tool", limit=3, ranker=_ranked(gateway), log=log
    )

    assert bomb.calls == 0
    assert hits == await Memory(log=log).retrieve("umbrella tool", limit=3)
    assert not [e for e in log.replay() if e.event_type == MEMORY_RETRIEVE_RERANKED]


async def test_a5_retrieve_does_not_mutate_caller_fold_maps(tmp_path):
    """A5 — Aliasing: retrieve() must not mutate the caller's memories/traces
    dicts even though MemoryIndex's inner dicts are pydantic-frozen-shell
    mutable; probing includes a model rerank + audit write."""
    log = _log(tmp_path)
    await _seed(log)
    index = MemoryIndex.rebuild(log)
    mem_before = {k: dict(v) for k, v in index.memories.items()}
    trc_before = {k: dict(v) for k, v in index.traces.items()}

    fake = _DrainAdapter([{"scores": [1.0, 0.0]}])
    gateway, reg = _gateway_with(fake)
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())

    await Memory(index=index).retrieve(
        "umbrella tool", limit=3, ranker=ModelRetrievalRanker(gateway), log=log
    )

    assert {k: dict(v) for k, v in index.memories.items()} == mem_before
    assert {k: dict(v) for k, v in index.traces.items()} == trc_before


# ---------------------------------------------------------------------------
# B. Total order (-score, tier_order, event_id) — offline + rerank seams
# ---------------------------------------------------------------------------

async def test_b1_offline_total_order_memory_before_trace_event_id_tiebreak(tmp_path):
    """B1 — Offline ranker None: total order is (-score, tier, event_id); an
    equal-scoring verified memory deterministically outranks a raw trace."""
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="umbrella is a company", source="s")
    MemoryTraceWriter(log).record_episodic(content="safe word umbrella", source="agent.run")

    hits = await Memory(log=log).retrieve("umbrella", limit=3)

    assert len(hits) == 2
    assert hits[0].score == hits[1].score
    assert hits[0].tier == "memory"
    assert hits[0].verified is True
    assert hits[1].tier == "trace"


async def test_b2_rerank_equal_scores_drop_tier_order_trace_wins(tmp_path):
    """B2 — RECONCILED (FLIPPED): the rerank sort key now carries tier_order
    (FB-M2.2-2), so on equal model scores the verified memory deterministically
    outranks the raw trace — the FB-1 discriminator holds on the model seam.
    Regression pin: contract order, (-score, tier_order, event_id)."""

    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _DrainAdapter([{"scores": [1.0, 1.0]}])  # equal scores -> tie
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    mem = RankedMemory(
        event_id="0ZZZZZZZZZZZZZZZZZZZZZZZZZZ",
        content="verified memory",
        source="s",
        score=1.0,
        tier="memory",
        verified=True,
    )
    trc = RankedMemory(
        event_id="000000000000000000000000000",
        content="raw trace",
        source="a",
        score=1.0,
        tier="trace",
        verified=False,
    )

    result = await ranker.rerank("q", [mem, trc], limit=2)

    assert result.reranked is True
    # FLIPPED ON FIX: verified memory wins the equal-score tie even though its
    # event_id sorts AFTER the raw trace's.
    assert [h.tier for h in result.ranked] == ["memory", "trace"]


async def test_b3_rerank_distinct_scores_reorders_deterministically(tmp_path):
    """B3 — With model scores that differ, the rerank reorders deterministically
    and still yields a total order (regression pin, acceptable behavior)."""
    log = _log(tmp_path)
    await _seed(log)
    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _DrainAdapter([{"scores": [0.1, 0.9]}])
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})

    hits1 = await Memory(log=log).retrieve(
        "umbrella tool", limit=3, ranker=ModelRetrievalRanker(gateway), log=log
    )
    fake2 = _DrainAdapter([{"scores": [0.1, 0.9]}])
    reg2 = CapabilityRegistry()
    reg2.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    gateway2 = ModelGateway(resolver=reg2, adapters={"model.adapter": fake2})
    hits2 = await Memory(log=log).retrieve(
        "umbrella tool", limit=3, ranker=ModelRetrievalRanker(gateway2), log=log
    )

    assert [h.model_dump() for h in hits1] == [h.model_dump() for h in hits2]
    assert hits1[0].score == 0.9
    assert hits1[0].tier == "trace"


# ---------------------------------------------------------------------------
# C. Tier / verified semantics (FB-1)
# ---------------------------------------------------------------------------

async def test_c1_dual_fold_id_trace_content_labeled_verified_memory(tmp_path):
    """C1 — RECONCILED (FLIPPED): the union merge is memories-win-BOTH (FB-M2.2-5).
    An id in both folds serves the MEMORY payload with tier=memory/verified=True,
    so a raw trace can never be stamped as a verified memory and the served
    content always agrees with the tier tag. Regression pin."""

    memories = {"A": {"content": "the safe word is umbrella", "source": "s"}}
    traces = {"A": {"content": "RAW TRACE claims umbrella", "source": "agent.run"}}

    hits = await retrieve(memories, traces, "umbrella", limit=3)

    assert len(hits) == 1
    assert hits[0].content == "the safe word is umbrella"
    assert hits[0].tier == "memory"
    assert hits[0].verified is True


def test_c2_ranked_memory_literal_tier_and_extra_forbid():
    """C2 — RankedMemory enforces Literal["memory","trace"] and rejects extra
    fields (schema abuse: tier not a literal, smuggling via args)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RankedMemory(
            event_id="e", content="c", source="s", score=0.5,
            tier="evil", verified=False,
        )
    with pytest.raises(ValidationError):
        RankedMemory(
            event_id="e", content="c", source="s", score=0.5,
            tier="memory", verified=False, smuggled=1,
        )
    m = RankedMemory(
        event_id="e", content="c", source="s", score=0.5,
        tier="trace", verified=False,
    )
    assert m.tier == "trace"
    assert m.model_config["extra"] == "forbid"


def test_c3_verified_bool_lax_coercion():
    """C3 — RECONCILED (FLIPPED): RankedMemory is strict (FB-M2.2-6); bool-ish
    int/str input for `verified` is REJECTED, not coerced. All fields are
    exactly typed. Regression pin."""

    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RankedMemory(
            event_id="e", content="c", source="s", score=0.5,
            tier="memory", verified=1,
        )
    with pytest.raises(ValidationError):
        RankedMemory(
            event_id="e2", content="c", source="s", score=0.5,
            tier="memory", verified="false",
        )


# ---------------------------------------------------------------------------
# D. role_contracts seam (module-6 additive kwarg)
# ---------------------------------------------------------------------------

async def test_d1_m1_routing_preserved_when_kwarg_absent():
    """D1 — With role_contracts=None the M1 route table is used bit-identical:
    SCHEMA_CONSTRAINED still resolves to model.generate_structured (module-6
    frozen contract preserved)."""
    registry = CapabilityRegistry.seed_m1_defaults()
    fake = _DrainAdapter([{"scores": [0.5]}])
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": fake})
    out = await gateway.generate_structured(
        RoleContract.SCHEMA_CONSTRAINED, RerankScores, input_text="x"
    )
    assert isinstance(out, ValidatedOutput)
    assert out.contract_id == "model.generate_structured"
    assert out.role_contract == RoleContract.SCHEMA_CONSTRAINED


async def test_d2_extra_routes_can_shadow_m1_schema_constrained(tmp_path):
    """D2 — The {**M1, **extra} merge makes SCHEMA_CONSTRAINED OVERRIDABLE:
    a caller can reroute the frozen module-6 role to another contract for one
    call. Contract A ratifies this merge order, so it is compliant — but it is
    also the seam that a later bug (a shared role_contracts dict built from
    M2_ROLE_CONTRACTS + a stray EMBED override) could exploit to move
    SCHEMA_CONSTRAINED off model.generate_structured. Pinned as evidence."""

    registry = CapabilityRegistry.seed_m1_defaults()
    fake = _DrainAdapter([{"scores": []}])
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": fake})

    out = await gateway.generate_structured(
        RoleContract.SCHEMA_CONSTRAINED,
        RerankScores,
        input_text="x",
        role_contracts={RoleContract.SCHEMA_CONSTRAINED: ("fs.write", "^1.0")},
    )

    # fs.write is only exposed by fs.default, which has no runtime adapter bound
    # here, so the gateway returns a typed failure AFTER re-routing (proving the
    # M1 route was consulted-then-replaced, not a no_provider on schema_constrained).
    assert isinstance(out, TypedFailure)
    assert out.reason == "adapter_error"


async def test_d3_ranker_partial_override_missing_rerank_falls_back_safely(tmp_path):
    """D3 — A ModelRetrievalRanker constructed with a role_contracts override
    that omits RERANK cannot resolve memory.rerank; the gateway yields
    unsupported_contract -> deterministic fallback, no raise, no audit."""
    log = _log(tmp_path)
    await _seed(log)
    bomb = _BombAdapter()
    registry = CapabilityRegistry.seed_m1_defaults()
    registry.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": bomb})

    ranker = ModelRetrievalRanker(
        gateway,
        role_contracts={RoleContract.EMBED: ("memory.embed", "^1.0")},
    )
    hits = await Memory(log=log).retrieve("umbrella", limit=3, ranker=ranker, log=log)

    assert bomb.calls == 0  # EMBED override must not cause a RERANK dial
    assert ranker.last_result is not None and ranker.last_result.reranked is False
    # FLIPS ON FIX (no change expected): hits are the deterministic lexical set
    assert hits == await Memory(log=log).retrieve("umbrella", limit=3)
    assert not [e for e in log.replay() if e.event_type == MEMORY_RETRIEVE_RERANKED]


# ---------------------------------------------------------------------------
# E. ModelRetrievalRanker fallback matrix + score smuggling
# ---------------------------------------------------------------------------

async def test_e1_nan_scores_accepted_rerank_and_audit(tmp_path):
    """E1 — RECONCILED (FLIPPED): RerankScores now REJECTS NaN (strict float,
    allow_inf_nan=False, FB-M2.2-1), so a NaN-emitting model exhausts the
    ADR-006 validation retries and falls back to the deterministic lexical
    order — reranked=False, NO audit, no NaN in any returned score.
    Regression pin: garbage scores can never be an audit-worthy success."""

    log = _log(tmp_path)
    await _seed(log)
    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _DrainAdapter([{"scores": [float("nan"), 0.5]}])
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    hits = await Memory(log=log).retrieve("umbrella", limit=3, ranker=ranker, log=log)

    assert ranker.last_result is not None and ranker.last_result.reranked is False
    assert fake.calls == 3
    assert hits == await Memory(log=log).retrieve("umbrella", limit=3)
    assert not any(math.isnan(h.score) for h in hits)
    assert not [e for e in log.replay() if e.event_type == MEMORY_RETRIEVE_RERANKED]


async def test_e2_infinite_scores_accepted_and_rank_dominance(tmp_path):
    """E2 — RECONCILED (FLIPPED): ±inf is equally rejected at the schema
    (FB-M2.2-1). A provider emitting infinities falls back to the deterministic
    lexical order: candidates unchanged, reranked=False, no non-finite score.
    Regression pin."""

    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _DrainAdapter([{"scores": [float("inf"), 0.5, float("-inf")]}])
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    cands = [
        RankedMemory(
            event_id="A" * 26, content=str(i), source="s", score=1.0,
            tier="memory", verified=True,
        )
        for i in range(3)
    ]
    result = await ranker.rerank("q", cands, limit=3)

    assert result.reranked is False
    assert [h.event_id for h in result.ranked] == [c.event_id for c in cands]
    assert all(math.isfinite(h.score) for h in result.ranked)


async def test_e3_score_count_mismatch_falls_back_lexical_no_audit(tmp_path):
    """E3 — len(scores) != len(candidates) -> deterministic lexical fallback,
    reranked=False, no audit, never raises, never partially reorders."""
    log = _log(tmp_path)
    await _seed(log)
    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _DrainAdapter([{"scores": [0.9]}])
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    hits = await Memory(log=log).retrieve("umbrella", limit=3, ranker=ranker, log=log)

    assert ranker.last_result is not None and ranker.last_result.reranked is False
    assert hits == await Memory(log=log).retrieve("umbrella", limit=3)
    assert not [e for e in log.replay() if e.event_type == MEMORY_RETRIEVE_RERANKED]


async def test_e4_validation_exhausted_after_3_garbage_attempts(tmp_path):
    """E4 — All three validation attempts fail -> validation_exhausted
    TypedFailure -> lexical fallback, no raise, no audit (ADR-006 path)."""
    log = _log(tmp_path)
    await _seed(log)
    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _DrainAdapter([{"scores": "oops"}, {"scores": "oops"}, {"scores": "oops"}])
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    hits = await Memory(log=log).retrieve("umbrella", limit=3, ranker=ranker, log=log)

    assert fake.calls == 3
    assert ranker.last_result is not None and ranker.last_result.reranked is False
    assert hits == await Memory(log=log).retrieve("umbrella", limit=3)
    assert not [e for e in log.replay() if e.event_type == MEMORY_RETRIEVE_RERANKED]


async def test_e5_transport_error_falls_back_no_raise(tmp_path):
    """E5 — ProviderTransportError -> transport_error TypedFailure -> lexical
    fallback; the adapters map is never re-dialled on the offline path."""
    log = _log(tmp_path)
    await _seed(log)
    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _RaiseAdapter(ProviderTransportError("network down"))
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    hits = await Memory(log=log).retrieve("umbrella", limit=3, ranker=ranker, log=log)

    assert fake.calls == 1
    assert ranker.last_result is not None and ranker.last_result.reranked is False
    assert hits == await Memory(log=log).retrieve("umbrella", limit=3)


async def test_e6_adapter_error_falls_back_no_raise(tmp_path):
    """E6 — A generic adapter exception -> adapter_error TypedFailure -> lexical
    fallback, no raise."""
    log = _log(tmp_path)
    await _seed(log)
    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _RaiseAdapter(RuntimeError("boom"))
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    hits = await Memory(log=log).retrieve("umbrella", limit=3, ranker=ranker)

    assert ranker.last_result is not None and ranker.last_result.reranked is False
    assert hits == await Memory(log=log).retrieve("umbrella", limit=3)


async def test_e7_no_provider_path_reranked_false(tmp_path):
    """E7 — no_provider (no binding registered for memory.rerank@^1.0) is also a
    deterministic fallback; TypedFailure.reason == no_provider, no audit."""
    log = _log(tmp_path)
    await _seed(log)
    bomb = _BombAdapter()
    registry = CapabilityRegistry.seed_m1_defaults()
    gateway = ModelGateway(resolver=registry, adapters={})
    ranker = ModelRetrievalRanker(gateway)

    hits = await Memory(log=log).retrieve("umbrella", limit=3, ranker=ranker, log=log)

    assert ranker.last_result is not None and ranker.last_result.reranked is False
    assert bomb.calls == 0
    assert hits == await Memory(log=log).retrieve("umbrella", limit=3)
    assert not [e for e in log.replay() if e.event_type == MEMORY_RETRIEVE_RERANKED]


async def test_e8_bool_scores_coerce_to_float(tmp_path):
    """E8 — RECONCILED (FLIPPED): the rerank schema is STRICT (FB-M2.2-6);
    bool is not a float, so [True, False] is REJECTED and the pass falls back
    to the deterministic lexical order. Regression pin: no type-smuggled
    scores are ever treated as a model success."""

    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _DrainAdapter([{"scores": [True, False]}])
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    cands = [
        RankedMemory(
            event_id="A" * 26, content="a", source="s", score=1.0,
            tier="memory", verified=True,
        ),
        RankedMemory(
            event_id="B" * 26, content="b", source="s", score=1.0,
            tier="trace", verified=False,
        ),
    ]
    result = await ranker.rerank("q", cands, limit=2)

    assert result.reranked is False
    assert [h.event_id for h in result.ranked] == [c.event_id for c in cands]


async def test_e9_numeric_string_scores_coerce_to_float(tmp_path):
    """E9 — RECONCILED (FLIPPED): numeric strings are not floats under the
    strict schema (FB-M2.2-6); a provider emitting them falls back to the
    deterministic lexical order. Regression pin."""

    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _DrainAdapter([{"scores": ["0.9", "0.1"]}])
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    cands = [
        RankedMemory(
            event_id="A" * 26, content="a", source="s", score=1.0,
            tier="memory", verified=True,
        ),
        RankedMemory(
            event_id="B" * 26, content="b", source="s", score=1.0,
            tier="trace", verified=False,
        ),
    ]
    result = await ranker.rerank("q", cands, limit=2)

    assert result.reranked is False
    assert [h.event_id for h in result.ranked] == [c.event_id for c in cands]


async def test_e10_negative_scores_reorder_bottom(tmp_path):
    """E10 — Negative scores are accepted (legit for a model's preference
    signal); they sort below positives via the -score key. Pinned acceptable."""

    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _DrainAdapter([{"scores": [-1.0, 1.0]}])
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    cands = [
        RankedMemory(
            event_id="A" * 26, content="a", source="s", score=1.0,
            tier="memory", verified=True,
        ),
        RankedMemory(
            event_id="B" * 26, content="b", source="s", score=1.0,
            tier="trace", verified=False,
        ),
    ]
    result = await ranker.rerank("q", cands, limit=2)

    assert result.reranked is True
    assert [h.score for h in result.ranked] == [1.0, -1.0]


async def test_e11_empty_candidates_no_dial_no_raise(tmp_path):
    """E11 — Empty candidate set with a bound ranker: returns [] without a
    model dial and without raising."""

    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    bomb = _BombAdapter()
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": bomb})
    ranker = ModelRetrievalRanker(gateway)

    result = await ranker.rerank("q", [], limit=3)

    assert result.ranked == []
    assert result.reranked is False
    assert bomb.calls == 0
    assert await retrieve({}, {}, "anything", limit=3) == []


async def test_e12_huge_limit_is_safe_and_bounded_by_candidates(tmp_path):
    """E12 — A huge limit is validated positive but naturally bounded by the
    candidate set; no blow-up, no partial order."""
    log = _log(tmp_path)
    await _seed(log)

    hits = await Memory(log=log).retrieve("umbrella", limit=1_000_000)

    assert len(hits) == 2


async def test_e13_custom_ranker_exception_propagates(tmp_path):
    """E13 — A user-supplied ranker that raises is NOT trapped by retrieve();
    the RuntimeError propagates to the caller. Only ModelRetrievalRanker carries
    the 'never raise' guarantee (contract B). Pinned as current behavior."""

    class _BombRanker:
        async def rerank(self, query, candidates, *, limit):
            raise RuntimeError("custom ranker bug")

    log = _log(tmp_path)
    await _seed(log)

    with pytest.raises(RuntimeError):
        await Memory(log=log).retrieve("umbrella", limit=3, ranker=_BombRanker())


# ---------------------------------------------------------------------------
# H. Payload-shape parity + malformed fold input (schema edge cases)
# ---------------------------------------------------------------------------

async def test_h1_ranked_hit_fields_match_underlying_payload(tmp_path):
    """H1 — RankedMemory content/source mirror the folded event payload that
    memory_api.get() returns; tier/verified track fold membership. Payload
    shape stays in sync with the underlying memory.write.committed /
    memory.trace.recorded events (event_id -> payload)."""
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="umbrella is a company", source="handbook")
    MemoryTraceWriter(log).record_episodic(
        content="safe word umbrella", source="agent.run"
    )
    memory = Memory(log=log)

    for hit in await memory.retrieve("umbrella", limit=3):
        payload = memory.get(hit.event_id)
        assert payload is not None
        assert hit.content == payload["content"]
        assert hit.source == payload["source"]
        if hit.tier == "memory":
            assert hit.verified is True
            assert [e for e in log.replay() if e.event_id == hit.event_id][0].event_type == (
                "memory.write.committed"
            )
        else:
            assert hit.verified is False
            assert [e for e in log.replay() if e.event_id == hit.event_id][0].event_type == (
                "memory.trace.recorded"
            )


async def test_h2_malformed_non_dict_fold_payload_raises_untyped(tmp_path):
    """H2 — RECONCILED (FLIPPED): malformed fold maps now raise a TYPED
    ValueError on the public retrieve(memories=, traces=) seam (FB-M2.2-8),
    never a raw pydantic exception. Regression pin."""

    with pytest.raises(ValueError, match="fold maps"):
        await retrieve({"A": "not-a-dict"}, {}, "anything", limit=3)


async def test_h3_unicode_only_content_never_retrieved(tmp_path):
    """H3 — The module-11 lexical funnel tokenizes [a-z0-9]+ only, so unicode-
    only content never scores and is invisible to retrieve() — byte-parity with
    recall() is preserved (INFO: frozen module-11 limitation, not M2.2's)."""
    hits = await retrieve(
        {"B": {"content": "巴黎是一个城市", "source": "s"}}, {}, "巴黎", limit=3
    )
    assert hits == []

    mixed = await retrieve(
        {"B": {"content": "巴黎 Paris city", "source": "s"}}, {}, "paris", limit=3
    )
    assert len(mixed) == 1
    assert mixed[0].score == 1.0


# ---------------------------------------------------------------------------
# F. Audit event ("memory.retrieve.reranked")
# ---------------------------------------------------------------------------

async def test_f1_default_facade_path_runs_model_but_drops_audit(tmp_path):
    """F1 — RECONCILED (FLIPPED): the facade defaults the audit log to its OWN
    EventLog (FB-M2.2-4), so the natural path `Memory(log=log).retrieve(..., 
    ranker=...)` audits a real rerank without the caller re-passing log=.
    Regression pin: a genuine rerank ALWAYS leaves its audit trail."""

    log = _log(tmp_path)
    await _seed(log)
    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _DrainAdapter([{"scores": [1.0, 0.0]}])
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    hits = await Memory(log=log).retrieve("umbrella", limit=3, ranker=ranker)

    assert ranker.last_result is not None and ranker.last_result.reranked is True
    assert fake.calls == 1
    audits = [e for e in log.replay() if e.event_type == MEMORY_RETRIEVE_RERANKED]
    assert len(audits) == 1


async def test_f2_offline_path_never_audits(tmp_path):
    """F2 — NoOp path (ranker=None) must never emit memory.retrieve.reranked,
    even when log= is supplied. Offline logs stay byte-identical."""
    log = _log(tmp_path)
    await _seed(log)
    before = [(e.event_id, e.payload_sha256, e.event_sha256) for e in log.replay()]

    await Memory(log=log).retrieve("umbrella", limit=3, log=log)

    after = [(e.event_id, e.payload_sha256, e.event_sha256) for e in log.replay()]
    assert before == after
    assert not [e for e in log.replay() if e.event_type == MEMORY_RETRIEVE_RERANKED]


async def test_f3_audit_payload_field_sanity(tmp_path):
    """F3 — Payload sanity: provider/contract/version/limit are present; the
    candidate_event_ids are the PRE-rerank lexical candidate ids (the input set,
    input order), not the output order. Pinned as the documented payload shape."""

    log = _log(tmp_path)
    await _seed(log)
    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _DrainAdapter([{"scores": [0.1, 0.9]}])
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    expected = [h.event_id for h in await Memory(log=log).retrieve("umbrella", limit=3)]
    hits = await Memory(log=log).retrieve(
        "umbrella", limit=3, ranker=ranker, log=log
    )

    audit = [e for e in log.replay() if e.event_type == MEMORY_RETRIEVE_RERANKED]
    assert len(audit) == 1
    p = audit[0].payload
    assert p["provider_id"] == "model.adapter"
    assert p["contract_id"] == "memory.rerank"
    assert p["contract_version"] == "1.0.0"
    assert p["limit"] == 3
    assert p["candidate_event_ids"] == expected
    assert len(p["candidate_event_ids"]) == min(2, 3)
    assert [e.event_id for e in hits] != p["candidate_event_ids"]  # rerank reordered


async def test_f4_audit_event_does_not_enter_memory_folds(tmp_path):
    """F4 — The rerank audit stays OUT of the memories/traces folds (fold
    predicates unchanged) — MemoryIndex continues to project only
    memory.write.committed + memory.trace.recorded."""
    log = _log(tmp_path)
    await _seed(log)
    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _DrainAdapter([{"scores": [1.0, 0.0]}])
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    idx_before = MemoryIndex.rebuild(log)
    await Memory(log=log).retrieve("umbrella", limit=3, ranker=ranker, log=log)
    idx_after = MemoryIndex.rebuild(log)

    assert idx_after.memories == idx_before.memories
    assert idx_after.traces == idx_before.traces


async def test_f5_audit_changes_index_digest_metadata(tmp_path):
    """F5 — RECONCILED (RULING, FB-M2.2-3): the audit event NEVER enters the
    memories/traces FOLDS — the fold CONTENT (the digest's semantics) is
    stable. The digest VALUE is append-position-sensitive (ANY appended event
    bumps last_seq/event_count/streams; this is M2.1 semantics for traces too),
    so the promise is fold-content stability, not digest-value stability.
    Regression pins both halves."""

    log = _log(tmp_path)
    await _seed(log)
    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _RepeatAdapter({"scores": [1.0, 0.0]})  # every call reranks
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    idx_before = MemoryIndex.rebuild(log)
    await Memory(log=log).retrieve("umbrella", limit=3, ranker=ranker, log=log)
    await Memory(log=log).retrieve("umbrella", limit=3, ranker=ranker, log=log)
    idx_after = MemoryIndex.rebuild(log)

    assert idx_after.memories == idx_before.memories
    assert idx_after.traces == idx_before.traces
    assert idx_before.last_seq < idx_after.last_seq
    assert idx_before.event_count < idx_after.event_count


async def test_f6_audit_stamped_creator_principal(tmp_path):
    """F6 — RECONCILED (FLIPPED): retrieve()/Memory.retrieve accept the CALLER's
    principal_id and stamp it onto the audit event (FB-M2.2-7); the default is
    the creator principal. Regression pin: agent-triggered reranks leave
    agent-authored provenance."""

    log = _log(tmp_path)
    await _seed(log)
    reg = CapabilityRegistry()
    reg.register_provider(CREATOR_PRINCIPAL_ID, _rerank_binding())
    fake = _DrainAdapter([{"scores": [1.0, 0.0]}])
    gateway = ModelGateway(resolver=reg, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    await Memory(log=log).retrieve(
        "umbrella", limit=3, ranker=ranker, principal_id="model.agent"
    )

    audit = [e for e in log.replay() if e.event_type == MEMORY_RETRIEVE_RERANKED]
    assert audit[0].principal_id == "model.agent"