from __future__ import annotations

"""Memory API facade (M2.1, spec §M2).

A thin deterministic wrapper over the read-side folds. `recall()` runs
module-11 lexical semantics over the UNION of committed memories and episodic
traces by delegating to the frozen module-11 retriever over a combined view,
so ordering stays module-11's total order (-score, event_id) and behavior is
bit-identical to module 11 whenever no traces exist.

M2.1 recall is NOT embedding/rerank-ranked — that ranking seam is M2.2.
`retrieve()` (M2.2, additive) adds ranked hits with fold tier/verification and
an optional model-backed rerank seam over the SAME combined view.
`get()` and `digest()` expose the underlying `MemoryIndex` fold.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .event_log import EventLog
from .memory_consolidate import ConsolidationPolicy, ConsolidationResult, MemoryConsolidator
from .memory_index import MemoryIndex
from .memory_projection import MemoryProjection
from .memory_query import RecalledMemory, recall as _index_recall
from .memory_retrieval import RankedMemory, RetrievalRanker, retrieve as _retrieve


class _CombinedView(BaseModel):
    """Duck-typed memory map view so `memory_query.recall` scores the union."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    memories: dict[str, dict[str, Any]] = Field(default_factory=dict)


class Memory:
    """Deterministic memory API over committed memories and episodic traces.

    Construct from an `EventLog` (rebuilds `MemoryIndex`), or inject an
    existing `MemoryIndex` / module-7 `MemoryProjection` for tests.
    """

    def __init__(
        self,
        log: EventLog | None = None,
        *,
        index: MemoryIndex | None = None,
        projection: MemoryProjection | None = None,
    ) -> None:
        self._index: MemoryIndex | None = None
        self._projection: MemoryProjection | None = None
        self._log: EventLog | None = log
        if index is not None:
            self._index = index
        elif projection is not None:
            self._projection = projection
        elif log is not None:
            self._index = MemoryIndex.rebuild(log)
        else:
            raise ValueError("Memory requires an EventLog, MemoryIndex, or MemoryProjection")

    @property
    def index(self) -> MemoryIndex | None:
        return self._index

    def _combined(self) -> dict[str, dict[str, Any]]:
        if self._index is not None:
            return {**self._index.memories, **self._index.traces}
        return dict(self._projection.memories)  # type: ignore[union-attr]

    def recall(self, query: str, *, limit: int = 3) -> list[RecalledMemory]:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("limit must be a positive integer")
        return _index_recall(_CombinedView(memories=self._combined()), query, limit=limit)

    async def retrieve(
        self,
        query: str,
        *,
        limit: int = 3,
        ranker: RetrievalRanker | None = None,
        log: EventLog | None = None,
        principal_id: str = "creator",
    ) -> list[RankedMemory]:
        """M2.2 additive seam: ranked retrieval over the same combined view as
        `recall()`, with fold tier/verification per hit (FB-1) and an optional
        model-backed reranker. `recall()` is untouched.

        Audit (FB-M2.2-4): when no `log` is given it defaults to the facade's
        OWN EventLog (if any), so `Memory(log=log).retrieve(..., ranker=...)`
        always leaves the audit trail for a real rerank. `principal_id` stamps
        the audit event (FB-M2.2-7)."""
        audit_log = log if log is not None else getattr(self, "_log", None)
        if self._index is not None:
            return await _retrieve(
                self._index.memories,
                self._index.traces,
                query,
                limit=limit,
                ranker=ranker,
                log=audit_log,
                principal_id=principal_id,
            )
        return await _retrieve(
            dict(self._projection.memories),  # type: ignore[union-attr]
            {},
            query,
            limit=limit,
            ranker=ranker,
            log=audit_log,
            principal_id=principal_id,
        )

    def consolidate(
        self,
        *,
        policy: ConsolidationPolicy | None = None,
        principal_id: str | None = None,
    ) -> ConsolidationResult:
        """M2.3 additive seam: promote raw episodic traces into durable memory
        (§84.3 two-tier). Deterministic, hermetic (no model calls, no effects),
        decided by the DATA `ConsolidationPolicy`; promotions run the frozen
        module-10 write path.

        Requires an EventLog (the promotion appends `memory.write.*` events);
        `principal_id=None` defers to the policy's principal (default
        "creator"). `recall()`/`retrieve()`/`get()`/`digest()` are untouched."""
        if self._log is None:
            raise ValueError("Memory.consolidate requires an EventLog")
        return MemoryConsolidator(
            self._log, policy=policy, principal_id=principal_id
        ).consolidate()

    def get(self, event_id: str) -> dict[str, Any] | None:
        if self._index is not None:
            hit = self._index.memories.get(event_id)
            return hit if hit is not None else self._index.traces.get(event_id)
        return self._projection.memories.get(event_id)  # type: ignore[union-attr]

    def digest(self) -> str:
        if self._index is not None:
            return self._index.digest()
        return self._projection.digest()  # type: ignore[union-attr]

    @property
    def memory_count(self) -> int:
        if self._index is not None:
            return len(self._index.memories)
        return len(self._projection.memories)  # type: ignore[union-attr]

    @property
    def trace_count(self) -> int:
        if self._index is None:
            return 0
        return len(self._index.traces)