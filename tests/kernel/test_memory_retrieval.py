from __future__ import annotations

"""M2.2 retrieval seam tests (spec §131.14 / docs/M2_2_KICKOFF.md, ratified)."""

import pytest

from jarvis.kernel.event_log import EventLog
from jarvis.kernel.memory_api import Memory
from jarvis.kernel.memory_index import MemoryIndex
from jarvis.kernel.memory_projection import MemoryProjection
from jarvis.kernel.memory_query import recall as module11_recall
from jarvis.kernel.memory_retrieval import (
    M2_ROLE_CONTRACTS,
    MEMORY_RETRIEVE_RERANKED,
    Embedder,
    ModelRetrievalRanker,
    RerankScores,
)
from jarvis.kernel.memory_trace import MemoryTraceWriter
from jarvis.kernel.memory_write import MemoryWriter
from jarvis.kernel.model_gateway import (
    M1_ROLE_CONTRACTS,
    ModelGateway,
    RoleContract,
    TypedFailure,
    ValidatedOutput,
)
from jarvis.kernel.registry import (
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


class _DrainingAdapter:
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
    provider_id = "model.adapter"

    def __init__(self):
        self.calls = 0

    async def invoke(self, contract_id, version, args):
        self.calls += 1
        return {}

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
            provenance_reason="M2.2 rerank seam test",
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


def _seed_with_rerank(log: EventLog) -> None:
    MemoryWriter(log).remember(content="umbrella is a company", source="s")
    MemoryTraceWriter(log).record_episodic(
        content="the tool works well here", source="agent.run"
    )


# ---------------------------------------------------------------------------
# Deterministic core: tiers, total order, limit, empty
# ---------------------------------------------------------------------------

async def test_retrieve_tags_memory_and_trace_tiers(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="the capital of France is Paris", source="s")
    MemoryTraceWriter(log).record_episodic(
        content="the safe word is umbrella", source="agent.run"
    )

    memory = Memory(log=log)
    trace_hits = await memory.retrieve("what is the safe word?", limit=3)
    assert [hit.tier for hit in trace_hits] == ["trace"]
    assert trace_hits[0].verified is False
    assert trace_hits[0].content == "the safe word is umbrella"

    memory_hits = await memory.retrieve("capital of France?", limit=3)
    assert [hit.tier for hit in memory_hits] == ["memory"]
    assert memory_hits[0].verified is True


async def test_retrieve_total_order_memory_before_trace_at_equal_score(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="umbrella is a company", source="s")
    MemoryTraceWriter(log).record_episodic(
        content="safe word umbrella", source="agent.run"
    )

    hits = await Memory(log=log).retrieve("umbrella", limit=3)

    assert len(hits) == 2
    assert {hit.tier for hit in hits} == {"memory", "trace"}
    assert hits[0].score == hits[1].score
    assert hits[0].tier == "memory"
    assert hits[1].tier == "trace"


async def test_retrieve_deterministic_across_rebuild(tmp_path):
    log = _log(tmp_path)
    _seed_with_rerank(log)
    MemoryTraceWriter(log).record_episodic(
        content="umbrella project started yesterday", source="agent.run"
    )

    first = await Memory(log=log).retrieve("umbrella", limit=3)
    second = await Memory(log=log).retrieve("umbrella", limit=3)

    assert [hit.model_dump() for hit in first] == [hit.model_dump() for hit in second]


async def test_retrieve_limit_validation(tmp_path):
    log = _log(tmp_path)
    _seed_with_rerank(log)
    memory = Memory(log=log)

    for bad in (0, -1, True, 1.5, "3"):
        with pytest.raises(ValueError):
            await memory.retrieve("umbrella", limit=bad)  # type: ignore[arg-type]


async def test_retrieve_no_match_and_empty_log_return_empty(tmp_path):
    empty = Memory(log=_log(tmp_path))
    assert await empty.retrieve("anything", limit=3) == []

    log = _log(tmp_path)
    _seed_with_rerank(log)
    assert await Memory(log=log).retrieve("xyzzyzz", limit=3) == []


# ---------------------------------------------------------------------------
# Offline path: no bound rerank provider, bogus backend never dialled
# ---------------------------------------------------------------------------

async def test_model_ranker_offline_falls_back_no_dial_no_audit(tmp_path):
    log = _log(tmp_path)
    _seed_with_rerank(log)
    registry = CapabilityRegistry.seed_m1_defaults()
    bomb = _BombAdapter()
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": bomb})
    ranker = ModelRetrievalRanker(gateway)

    hits = await Memory(log=log).retrieve("umbrella tool", limit=3, ranker=ranker, log=log)

    assert bomb.calls == 0
    assert ranker.last_result is not None
    assert ranker.last_result.reranked is False
    assert [hit.tier for hit in hits] == ["memory", "trace"]
    assert [event.event_type for event in log.replay()] == [
        "memory.write.proposed",
        "memory.write.verified",
        "memory.write.committed",
        "memory.trace.recorded",
    ]


# ---------------------------------------------------------------------------
# Model rerank seam: reorder, provenance, audit, validation fallback
# ---------------------------------------------------------------------------

async def test_model_rerank_reorders_and_audits(tmp_path):
    log = _log(tmp_path)
    _seed_with_rerank(log)
    registry = CapabilityRegistry()
    registry.register_provider("creator", _rerank_binding())
    fake = _DrainingAdapter([{"scores": [0.0, 1.0]}])
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)
    memory = Memory(log=log)

    hits = await memory.retrieve("umbrella tool", limit=3, ranker=ranker, log=log)

    assert len(hits) == 2
    assert hits[0].tier == "trace"
    assert hits[0].score == 1.0
    assert hits[1].tier == "memory"
    assert ranker.last_result is not None and ranker.last_result.reranked is True
    assert ranker.last_result.provider_id == "model.adapter"
    assert ranker.last_result.contract_id == "memory.rerank"
    assert ranker.last_result.contract_version == "1.0.0"
    assert fake.calls == 1

    rerank_events = [
        event for event in log.replay() if event.event_type == MEMORY_RETRIEVE_RERANKED
    ]
    assert len(rerank_events) == 1
    audit = rerank_events[0]
    assert audit.stream_id == "memory"
    assert audit.payload["contract_id"] == "memory.rerank"
    assert audit.payload["contract_version"] == "1.0.0"
    assert audit.payload["provider_id"] == "model.adapter"
    assert audit.payload["limit"] == 3
    assert len(audit.payload["candidate_event_ids"]) == 2


async def test_rerank_audit_uses_facade_log_by_default(tmp_path):
    log = _log(tmp_path)
    _seed_with_rerank(log)
    registry = CapabilityRegistry()
    registry.register_provider("creator", _rerank_binding())
    fake = _DrainingAdapter([{"scores": [1.0, 0.0]}])
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    await Memory(log=log).retrieve("umbrella tool", limit=3, ranker=ranker)

    audits = [e for e in log.replay() if e.event_type == MEMORY_RETRIEVE_RERANKED]
    assert len(audits) == 1


async def test_rerank_without_facade_log_writes_no_audit(tmp_path):
    log = _log(tmp_path)
    _seed_with_rerank(log)
    registry = CapabilityRegistry()
    registry.register_provider("creator", _rerank_binding())
    fake = _DrainingAdapter([{"scores": [1.0, 0.0]}])
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    memory = Memory(index=MemoryIndex.rebuild(log))
    await memory.retrieve("umbrella tool", limit=3, ranker=ranker)

    assert [e.event_type for e in log.replay()] == [
        "memory.write.proposed",
        "memory.write.verified",
        "memory.write.committed",
        "memory.trace.recorded",
    ]


async def test_rerank_schema_violation_falls_back_lexical(tmp_path):
    log = _log(tmp_path)
    _seed_with_rerank(log)
    registry = CapabilityRegistry()
    registry.register_provider("creator", _rerank_binding())
    fake = _DrainingAdapter([{"scores": "oops"}, {"scores": "oops"}, {"scores": "oops"}])
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    hits = await Memory(log=log).retrieve("umbrella tool", limit=3, ranker=ranker, log=log)

    assert ranker.last_result is not None and ranker.last_result.reranked is False
    assert [hit.tier for hit in hits] == ["memory", "trace"]
    assert fake.calls == 3
    assert not [e for e in log.replay() if e.event_type == MEMORY_RETRIEVE_RERANKED]


async def test_rerank_score_count_mismatch_falls_back_lexical(tmp_path):
    log = _log(tmp_path)
    _seed_with_rerank(log)
    registry = CapabilityRegistry()
    registry.register_provider("creator", _rerank_binding())
    fake = _DrainingAdapter([{"scores": [0.9]}])
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": fake})
    ranker = ModelRetrievalRanker(gateway)

    hits = await Memory(log=log).retrieve("umbrella tool", limit=3, ranker=ranker)

    assert ranker.last_result is not None and ranker.last_result.reranked is False
    assert hits == await Memory(log=log).retrieve("umbrella tool", limit=3)


# ---------------------------------------------------------------------------
# Gateway additive role_contracts seam (module 6, additive only)
# ---------------------------------------------------------------------------

async def test_gateway_role_contracts_kwarg_routes_extended_role():
    registry = CapabilityRegistry.seed_m1_defaults()
    fake = _DrainingAdapter([{"scores": [0.5, 0.9]}])
    gateway = ModelGateway(resolver=registry, adapters={"model.adapter": fake})
    extra = {RoleContract.RERANK: ("model.generate_structured", "^1.0")}

    result = await gateway.generate_structured(
        RoleContract.RERANK,
        RerankScores,
        input_text="candidates",
        role_contracts=extra,
    )

    assert isinstance(result, ValidatedOutput)
    assert result.value.scores == [0.5, 0.9]
    assert result.role_contract == RoleContract.RERANK


async def test_gateway_default_still_unsupported_for_rerank():
    registry = CapabilityRegistry.seed_m1_defaults()
    gateway = ModelGateway(resolver=registry, adapters={})

    result = await gateway.generate_structured(RoleContract.RERANK, RerankScores)

    assert isinstance(result, TypedFailure)
    assert result.reason == "unsupported_contract"


def test_m2_role_contracts_extends_m1_only():
    for role, route in M1_ROLE_CONTRACTS.items():
        assert M2_ROLE_CONTRACTS[role] == route
    assert set(M2_ROLE_CONTRACTS) - set(M1_ROLE_CONTRACTS) == {
        RoleContract.RERANK,
        RoleContract.EMBED,
    }
    assert M2_ROLE_CONTRACTS[RoleContract.RERANK] == ("memory.rerank", "^1.0")
    assert M2_ROLE_CONTRACTS[RoleContract.EMBED] == ("memory.embed", "^1.0")


def test_embed_seam_declared_as_protocol():
    assert hasattr(Embedder, "embed")


# ---------------------------------------------------------------------------
# Facade parity: retrieve shares the combine view, projection fallback works
# ---------------------------------------------------------------------------

async def test_retrieve_projection_fallback(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="umbrella is the safe word", source="s")
    projection = MemoryProjection.rebuild(log)

    hits = await Memory(projection=projection).retrieve("safe word", limit=1)

    assert len(hits) == 1
    assert hits[0].tier == "memory"
    assert hits[0].verified is True
    assert hits[0].score == 1.0


async def test_retrieve_matches_module11_lexical_when_no_traces(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="the capital of France is Paris", source="s")
    projection = MemoryProjection.rebuild(log)

    expected = module11_recall(projection, "what is the capital of France?", limit=3)
    retrieved = await Memory(projection=projection).retrieve(
        "what is the capital of France?", limit=3
    )
    assert [hit.content for hit in retrieved] == [hit.content for hit in expected]
    assert [hit.score for hit in retrieved] == [hit.score for hit in expected]
    assert all(hit.tier == "memory" and hit.verified is True for hit in retrieved)