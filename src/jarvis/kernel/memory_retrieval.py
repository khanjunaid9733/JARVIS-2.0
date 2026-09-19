from __future__ import annotations

"""M2.2 retrieval seams: ranked memory hits + replaceable embed/rerank roles.

Spec §131.14 requires embedding and reranking to be replaceable Model Fabric
providers — Memory OS roles bound behind the `ModelGateway` / `ProviderResolver`
substitution seam, never Memory OS identity. §134.1 keeps any external vector
index/DB out of the kernel: the deterministic lexical core works with NO model
provider at all (M1.1 / §127.1 precedent), and the model-backed rerank path is
a caller-opted seam (`ranker=`), never a kernel dependency.

This module is the M2.2 consumed boundary (drafted in `docs/M2_2_KICKOFF.md`,
ratified by the creator 2026-09-19):

1. `RankedMemory` — a hit carrying the FB-1 discriminator the M2.1 recall
   deferred: `tier` (`memory` vs `trace` fold) and `verified` (committed
   memory.write fold membership, §84.4 tier separation; semantic verification
   ladder is M2.4 and will deepen this field additively).
2. `retrieve()` — deterministic retrieval over the union of both folds.
   Candidate funnel is module-11 lexical scoring (bit-identical to M2.1
   `recall`); the total order is `(-score, tier_order, event_id)` with
   `tier_order` memory < trace, so an equal-scoring verified memory outranks a
   raw trace deterministically. No clock, no RNG, no network.
3. `ModelRetrievalRanker` — the §131.14 rerank seam: schema-validated scores
   via the gateway `RERANK` role, routed through caller-supplied route DATA
   (`M2_ROLE_CONTRACTS`). ANY gateway failure (no provider, transport,
   validation exhaustion, adapter error) falls back to the deterministic
   lexical order — never raises.
4. `Embedder` — the declared embed seam. Route DATA exists (`memory.embed`)
   but no consumer calls it in M2.2; the binding decision is M2.9 / creator.
5. Audit (`memory.retrieve.reranked`): recorded ONLY when a model rerank
   actually runs (provider bound + successful response), so offline logs carry
   no rerank events and the retriever needs no log to be deterministic.
"""

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict

from .event_log import Event, EventLog
from .memory_query import RecalledMemory, recall as _lexical_recall
from .memory_trace import MEMORY_STREAM_ID
from .model_gateway import M1_ROLE_CONTRACTS, ModelGateway, RoleContract, TypedFailure
from .registry import CREATOR_PRINCIPAL_ID

MEMORY_RETRIEVE_RERANKED = "memory.retrieve.reranked"
RERANK_SCHEMA_ID = "memory.rerank.v1"
TIER_ORDER: dict[str, int] = {"memory": 0, "trace": 1}


# M2.2 route DATA (spec §131.2/§131.14): role → contract handled by the model
# fabric. EMBED is declared for consumer seeding; the default ordering consumes
# only RERANK. M1_ROLE_CONTRACTS is imported, never mutated (module 6 frozen).
M2_ROLE_CONTRACTS: dict[RoleContract, tuple[str, str]] = {
    **M1_ROLE_CONTRACTS,
    RoleContract.RERANK: ("memory.rerank", "^1.0"),
    RoleContract.EMBED: ("memory.embed", "^1.0"),
}


class RankedMemory(BaseModel):
    """A retrieval hit with its fold provenance (FB-1 discriminator)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    content: str
    source: str
    score: float
    tier: Literal["memory", "trace"]
    verified: bool


class Embedder(Protocol):
    """Declared embed seam (§131.14). Optional; not consumed by M2.2 ordering.

    A future package binds `RoleContract.EMBED` via route DATA in
    `M2_ROLE_CONTRACTS` and implements this protocol against the gateway.
    """

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class RankerResult(BaseModel):
    """Outcome of one rerank pass; `reranked` records whether a model ran."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ranked: list[RankedMemory]
    reranked: bool = False
    provider_id: str | None = None
    contract_id: str | None = None
    contract_version: str | None = None


class RetrievalRanker(Protocol):
    """Provider-backed reorder seam over the deterministic candidate funnel."""

    async def rerank(
        self, query: str, candidates: list[RankedMemory], *, limit: int
    ) -> RankerResult: ...


class NoOpRanker:
    """Default ranker: candidates unchanged — the pure lexical path."""

    async def rerank(
        self, query: str, candidates: list[RankedMemory], *, limit: int
    ) -> RankerResult:
        return RankerResult(ranked=list(candidates[:limit]), reranked=False)


class RerankScores(BaseModel):
    """Schema-constrained rerank output (ADR-006 validated locally)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scores: list[float]


class ModelRetrievalRanker:
    """§131.14 rerank seam: model-backed reordering over the gateway.

    Falls back to the deterministic lexical order on ANY non-success gateway
    outcome (TypedFailure or score-count mismatch) — never raises, never
    partially reorders. Provenance of the last pass is on `last_result`.
    """

    def __init__(
        self,
        gateway: ModelGateway,
        *,
        role_contracts: dict[RoleContract, tuple[str, str]] | None = None,
    ) -> None:
        self._gateway = gateway
        self._role_contracts = (
            dict(role_contracts) if role_contracts is not None else dict(M2_ROLE_CONTRACTS)
        )
        self.last_result: RankerResult | None = None

    @staticmethod
    def _prompt(query: str, candidates: list[RankedMemory]) -> str:
        lines = [f"query: {query}", "candidates:"]
        for i, candidate in enumerate(candidates):
            lines.append(
                f"{i}. [{candidate.tier}] {candidate.content} "
                f"(lexicalScore={candidate.score})"
            )
        return "\n".join(lines)

    async def rerank(
        self, query: str, candidates: list[RankedMemory], *, limit: int
    ) -> RankerResult:
        if not candidates or limit < 1:
            result = RankerResult(ranked=list(candidates[:limit]), reranked=False)
            self.last_result = result
            return result

        output = await self._gateway.generate_structured(
            RoleContract.RERANK,
            RerankScores,
            schema_id=RERANK_SCHEMA_ID,
            input_text=self._prompt(query, candidates),
            role_contracts=self._role_contracts,
        )
        if isinstance(output, TypedFailure):
            result = RankerResult(ranked=list(candidates[:limit]), reranked=False)
            self.last_result = result
            return result

        scores = output.value.scores
        if len(scores) != len(candidates):
            result = RankerResult(ranked=list(candidates[:limit]), reranked=False)
            self.last_result = result
            return result

        pairs = sorted(
            zip(candidates, scores),
            key=lambda pair: (-round(float(pair[1]), 4), pair[0].event_id),
        )
        reranked = [
            candidate.model_copy(update={"score": round(float(score), 4)})
            for candidate, score in pairs
        ][:limit]
        result = RankerResult(
            ranked=reranked,
            reranked=True,
            provider_id=output.provider_id,
            contract_id=output.contract_id,
            contract_version=output.contract_version,
        )
        self.last_result = result
        return result


class _UnionView(BaseModel):
    """Duck-typed memory map so the frozen module-11 retriever scores the union."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    memories: dict[str, dict[str, Any]]


def _tier_for(
    event_id: str,
    memories: dict[str, dict[str, Any]],
    traces: dict[str, dict[str, Any]],
) -> tuple[str, bool]:
    """FB-1 provenance: fold membership decides tier and verifier status.

    Memories first: a ULID can never live in both folds (event ids are unique),
    but membership order is pinned for determinism if a log ever produces one.
    """
    if event_id in memories:
        return "memory", True
    return "trace", False


async def retrieve(
    memories: dict[str, dict[str, Any]],
    traces: dict[str, dict[str, Any]],
    query: str,
    *,
    limit: int = 3,
    ranker: RetrievalRanker | None = None,
    log: EventLog | None = None,
) -> list[RankedMemory]:
    """Deterministic retrieval over the memory + trace union (M2.2 core).

    Lexical funnel is module-11 over the same combined view M2.1 recall uses;
    total order is (-score, tier_order, event_id). `ranker` may reorder via the
    model fabric (§131.14); a real rerank is audited to `log` only when it runs.
    """
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer")

    combined: dict[str, dict[str, Any]] = {**memories, **traces}
    lexical: list[RecalledMemory] = _lexical_recall(
        _UnionView(memories=combined), query, limit=len(combined)
    )
    ranked: list[RankedMemory] = []
    for hit in lexical:
        tier, verified = _tier_for(hit.event_id, memories, traces)
        ranked.append(
            RankedMemory(
                event_id=hit.event_id,
                content=hit.content,
                source=hit.source,
                score=hit.score,
                tier=tier,
                verified=verified,
            )
        )
    ranked.sort(key=lambda hit: (-hit.score, TIER_ORDER[hit.tier], hit.event_id))
    ranked = ranked[:limit]

    effective = ranker if ranker is not None else NoOpRanker()
    result = await effective.rerank(query, ranked, limit=limit)

    if result.reranked and log is not None:
        log.append(
            Event(
                stream_id=MEMORY_STREAM_ID,
                event_type=MEMORY_RETRIEVE_RERANKED,
                principal_id=CREATOR_PRINCIPAL_ID,
                payload={
                    "provider_id": result.provider_id,
                    "contract_id": result.contract_id,
                    "contract_version": result.contract_version,
                    "candidate_event_ids": [hit.event_id for hit in ranked],
                    "limit": limit,
                },
            )
        )
    return result.ranked[:limit]