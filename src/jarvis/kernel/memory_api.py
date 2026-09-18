from __future__ import annotations

"""Memory API facade (M2.1, spec §M2).

A thin deterministic wrapper over the read-side folds. `recall()` runs
module-11 lexical semantics over the UNION of committed memories and episodic
traces by delegating to the frozen module-11 retriever over a combined view,
so ordering stays module-11's total order (-score, event_id) and behavior is
bit-identical to module 11 whenever no traces exist.

M2.1 recall is NOT embedding/rerank-ranked — that ranking seam is M2.2.
`get()` and `digest()` expose the underlying `MemoryIndex` fold.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .event_log import EventLog
from .memory_index import MemoryIndex
from .memory_projection import MemoryProjection
from .memory_query import RecalledMemory, recall as _index_recall


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
        if index is not None:
            self._index = index
        elif projection is not None:
            self._index = None
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
        return _index_recall(_CombinedView(memories=self._combined()), query, limit=limit)

    def get(self, event_id: str) -> dict[str, Any] | None:
        if self._index is not None:
            return self._index.memories.get(event_id) or self._index.traces.get(event_id)
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