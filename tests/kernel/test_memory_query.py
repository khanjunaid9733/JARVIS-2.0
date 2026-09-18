from __future__ import annotations

"""Module 11 deterministic recall/answer tests (§127.1 extractive path, F-D13)."""

from jarvis.kernel.event_log import EventLog
from jarvis.kernel.memory_projection import MemoryProjection
from jarvis.kernel.memory_query import ANSWER_MIN_CONFIDENCE, answer, recall
from jarvis.kernel.memory_write import MemoryWriter


class _FixedClock:
    def now_utc_iso(self) -> str:
        return "2026-09-18T00:00:00.000Z"


def _log(tmp_path) -> EventLog:
    return EventLog(db_path=str(tmp_path / "log.db"), clock=_FixedClock())


def test_recall_scores_token_overlap(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="the capital of France is Paris", source="s")
    projection = MemoryProjection.rebuild(log)

    hits = recall(projection, "what is the capital of France?", limit=1)

    assert len(hits) == 1
    assert hits[0].score == 1.0


def test_answer_good_overlap_answers(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="the capital of France is Paris", source="s")
    projection = MemoryProjection.rebuild(log)

    result = answer(projection, "what is the capital of France?")

    assert result.answered is True
    assert result.answer == "Paris"
    assert result.confidence == 1.0


def test_answer_low_overlap_is_not_answered(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="the capital of France is Paris", source="s")
    projection = MemoryProjection.rebuild(log)

    wrong = answer(projection, "how much capital does the umbrella company hold?")

    assert wrong.answered is False
    assert wrong.answer is None
    assert wrong.confidence < ANSWER_MIN_CONFIDENCE


def test_answer_no_hit_is_not_answered(tmp_path):
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="the safe word is umbrella", source="s")
    projection = MemoryProjection.rebuild(log)

    result = answer(projection, "what is the meaning of life?")

    assert result.answered is False
    assert result.answer is None
    assert result.confidence == 0.0