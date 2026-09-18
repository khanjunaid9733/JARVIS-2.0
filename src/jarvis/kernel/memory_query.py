from __future__ import annotations

"""Deterministic recall + extractive answer over committed memories (module 11).

The §127.1 smoke test needs `jarvis say "what is the safe word?" -> umbrella`.
M1 answers this from the committed memory projection with a deterministic,
offline lexical retriever — no model call, no network. The model-backed answer
path (structured `Answer` via the ModelGateway) is deferred to M1.1; the
deterministic extractive path keeps the acceptance gate reproducible on a
fresh machine without a configured backend. Disclosed in the module report.

Tie-break is `(-score, event_id)` so ranking is total and clock-independent.
"""

import re

from pydantic import BaseModel, ConfigDict

from .memory_projection import MemoryProjection

_WORD = re.compile(r"[a-z0-9]+")

_STOPWORDS = frozenset(
    "a an the is are was were be been being what which who whom whose of to in "
    "on for and or do does did this that these those it its i you he she they "
    "we me my your".split()
)

# F-D13: `answer()` only emits an answer when at least half of the query's
# non-stopword tokens overlap a remembered fact. Below the floor the CLI
# reports "no relevant memory" instead of a confident-sounding guess. The
# overlap score remains `confidence` (disclosed extractive scoring), and the
# floor prevents a token-overlap's-wrong-memory recall from being presented
# as an answer.
ANSWER_MIN_CONFIDENCE = 0.5


def _tokens(text: str) -> list[str]:
    return [token for token in _WORD.findall(text.lower()) if token not in _STOPWORDS]


class RecalledMemory(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    content: str
    source: str
    score: float


class AnswerResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    answered: bool
    answer: str | None
    confidence: float
    source: str | None
    memory_event_id: str | None


def recall(
    projection: MemoryProjection, query: str, *, limit: int = 1
) -> list[RecalledMemory]:
    query_tokens = set(_tokens(query))
    scored: list[RecalledMemory] = []
    for event_id, payload in projection.memories.items():
        content = str(payload.get("content", ""))
        content_tokens = set(_tokens(content))
        if not query_tokens or not content_tokens:
            score = 0.0
        else:
            score = len(query_tokens & content_tokens) / len(query_tokens)
        if score > 0.0:
            scored.append(
                RecalledMemory(
                    event_id=event_id,
                    content=content,
                    source=str(payload.get("source", "")),
                    score=round(score, 4),
                )
            )
    scored.sort(key=lambda hit: (-hit.score, hit.event_id))
    return scored[:limit]


def _extract(content: str) -> str:
    """Extract the asserted value from a declarative memory.

    'the safe word is umbrella' -> 'umbrella'. Falls back to the full content.
    """
    for marker in (" is ", " was ", " are ", " were ", " means "):
        if marker in content:
            return content.rsplit(marker, 1)[-1].strip().strip(".!?")
    return content.strip()


def answer(projection: MemoryProjection, query: str) -> AnswerResult:
    hits = recall(projection, query, limit=1)
    if not hits:
        return AnswerResult(
            answered=False,
            answer=None,
            confidence=0.0,
            source=None,
            memory_event_id=None,
        )
    top = hits[0]
    if top.score < ANSWER_MIN_CONFIDENCE:
        # F-D13: low token overlap is not an answer — report "not answered".
        return AnswerResult(
            answered=False,
            answer=None,
            confidence=top.score,
            source=None,
            memory_event_id=None,
        )
    return AnswerResult(
        answered=True,
        answer=_extract(top.content),
        confidence=top.score,
        source=top.source or None,
        memory_event_id=top.event_id,
    )
