from __future__ import annotations

"""Freebuff M2.1 red-team evidence probes — branch `task/m2.1` @ `af99696`.

These are EVIDENCE, not accepted architecture (Freebuff role contract). Each
test PINS the behavior observed on disk and names, in a comment, the behavior
the finding recommends. Assertions marked ``# FLIPS ON FIX`` are the ones that
must change when (and only when) the corresponding fix lands.

Targets: src/jarvis/kernel/memory_trace.py, memory_index.py, memory_api.py,
src/jarvis/cli.py (`_cmd_recall`).
"""

import pytest

from jarvis import cli
from jarvis.kernel.event_log import Event, EventLog
from jarvis.kernel.memory_api import Memory
from jarvis.kernel.memory_index import MemoryIndex
from jarvis.kernel.memory_projection import MemoryProjection
from jarvis.kernel.memory_trace import MemoryTraceWriter, TraceWriteResult
from jarvis.kernel.memory_write import MemoryWriter


class _FixedClock:
    def __init__(self, ts: str = "2026-09-19T00:00:00.000Z") -> None:
        self._ts = ts

    def now_utc_iso(self) -> str:
        return self._ts


def _log(tmp_path, name: str = "log.db") -> EventLog:
    return EventLog(db_path=str(tmp_path / name), clock=_FixedClock())


def _home(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.delenv("JARVIS_MODEL_API_KEY", raising=False)
    monkeypatch.delenv("JARVIS_MODEL_BASE_URL", raising=False)
    return tmp_path


# ---------------------------------------------------------------------------
# A. Episodic trace writer
# ---------------------------------------------------------------------------

def test_a1_evidence_as_bare_string_is_treated_as_one_ref(tmp_path):
    """A1 (reconciled) — a bare `str` is ONE reference, never char-split."""
    log = _log(tmp_path)
    result = MemoryTraceWriter(log).record_episodic(
        content="read evidence.json",
        source="agent.run",
        evidence="01ARZ3NDEKTSV4RRFFQ69G5FAV",
    )

    trace = log.replay()[0]
    assert trace.payload["evidence"] == ["01ARZ3NDEKTSV4RRFFQ69G5FAV"]
    assert trace.cause_event_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert result.status == "recorded"


def test_a2_non_iterable_evidence_is_a_typed_rejection(tmp_path):
    """A2 (reconciled) — non-sequence evidence returns a typed rejected result."""
    log = _log(tmp_path)
    result = MemoryTraceWriter(log).record_episodic(
        content="c", source="s", evidence=12345
    )
    assert result.status == "rejected"
    assert result.event_id is None
    assert result.gate is None
    assert "evidence" in result.reason  # type: ignore[union-attr]
    assert log.replay() == []


def test_a3_trace_result_exposes_correlation_id(tmp_path):
    """A3 (reconciled) — `TraceWriteResult.correlation_id` surfaces the effective
    correlation a caller must chain on."""
    assert "correlation_id" in TraceWriteResult.model_fields
    log = _log(tmp_path)
    result = MemoryTraceWriter(log).record_episodic(
        content="x", source="s", correlation_id="corr-42"
    )
    assert result.status == "recorded"
    assert result.correlation_id == "corr-42"
    assert log.replay()[0].correlation_id == "corr-42"


def test_a4_rejected_trace_leaves_no_audit_event(tmp_path):
    """A4 — a refused trace is invisible to replay/audit.

    Contract B says 'On gate failure no event is written', so this is
    CONTRACT-COMPLIANT — but module 10's writer appends `memory.write.rejected`
    for the same gate kind, so the two tiers disagree on whether a refusal is
    auditable (§112 causal discipline; same class as M1 finding F-A2). Creator
    ruling needed: asymmetry is intentional, or add `memory.trace.rejected`.
    """
    log = _log(tmp_path)
    result = MemoryTraceWriter(log).record_episodic(content="", source="s")

    assert result.status == "rejected"
    assert result.event_id is None
    assert log.replay() == []


def test_a5_trace_gate_rejects_bool_confidence_like_module_10(tmp_path):
    """A5 (reconciled via F-M2.1-2) — the trace tier must NOT coerce `bool`
    into a 1.0 confidence; it now hands the raw value to DoneGate which rejects
    it exactly like the module-10 writer does."""
    log = _log(tmp_path)
    memory = MemoryWriter(log).remember(content="alpha", source="s", confidence=True)
    trace = MemoryTraceWriter(log).record_episodic(
        content="beta", source="s", confidence=True
    )

    assert memory.status == "rejected"
    assert trace.status == "rejected"
    assert trace.reason is not None and "confidence_valid" in trace.reason
    assert [e.event_type for e in log.replay()] == [
        "memory.write.proposed",
        "memory.write.verified",
        "memory.write.rejected",
    ]


def test_a6_trace_gate_rejects_numeric_string_confidence_like_module_10(tmp_path):
    """A6 (reconciled via F-M2.1-2) — a numeric string is not coerced before the
    gate; it is rejected exactly like module 10."""
    log = _log(tmp_path)
    memory = MemoryWriter(log).remember(content="alpha", source="s", confidence="0.5")
    trace = MemoryTraceWriter(log).record_episodic(
        content="beta", source="s", confidence="0.5"
    )

    assert memory.status == "rejected"
    assert trace.status == "rejected"
    assert trace.reason is not None and "confidence_valid" in trace.reason
    assert log.replay()[0].event_type == "memory.write.proposed"


def test_a7_nan_confidence_is_caught_by_the_gate(tmp_path):
    """A7 (no-finding) — NaN survives `min(max(...))` but the gate rejects it, so
    no non-canonical JSON (`NaN`) can reach `payload_json` through the writer.
    """
    log = _log(tmp_path)
    result = MemoryTraceWriter(log).record_episodic(
        content="c", source="s", confidence=float("nan")
    )
    assert result.status == "rejected"
    assert log.replay() == []


# ---------------------------------------------------------------------------
# B. Combined projection
# ---------------------------------------------------------------------------

def test_b1_same_log_yields_two_different_nat03_digests(tmp_path):
    """B1 — two mutually incomparable 'NAT-03 canonical state' digests for one log,
    selected by the Memory facade's constructor path.

    project_state.yaml nat_03 defines the digest over module-7 state
    `(last_seq, event_count, streams, providers, memories)`; M2.1's
    `MemoryIndex.digest()` hashes a different state shape (no `providers`, adds
    `traces`). `Memory(log=...)` returns the new one, `Memory(projection=...)`
    the old one — so a restart/recover check that compares digests across the two
    construction paths reports spurious divergence for an identical log.
    """
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="alpha", source="s")
    MemoryTraceWriter(log).record_episodic(content="beta", source="s")

    index_digest = Memory(log=log).digest()
    projection_digest = Memory(projection=MemoryProjection.rebuild(log)).digest()

    assert index_digest != projection_digest  # same log, two "canonical" digests
    # ...while the retrieval answer is identical either way:
    assert Memory(log=log).recall("alpha", limit=3) == Memory(
        projection=MemoryProjection.rebuild(log)
    ).recall("alpha", limit=3)


def test_b2_memoryindex_digest_is_blind_to_provider_identity(tmp_path):
    """B2 — the M2.1 digest does not cover provider state.

    Two logs differing ONLY in which provider was registered produce the SAME
    `MemoryIndex.digest()` (the `streams` map only records per-stream sequence
    numbers) but DIFFERENT module-7 digests. So neither digest alone is the
    canonical state the NAT-03 ledger claims; M2 recovery needs one definition.
    """
    def _provider_log(name: str, provider_id: str) -> EventLog:
        log = _log(tmp_path, name)
        log.append(
            Event(
                stream_id="capability",
                event_type="capability.provider_added",
                principal_id="creator",
                payload={
                    "provider": {
                        "meta": {"provider_id": provider_id},
                        "contracts": [],
                    }
                },
            )
        )
        return log

    log_x = _provider_log("x.db", "prov.X")
    log_y = _provider_log("y.db", "prov.Y")

    assert MemoryIndex.rebuild(log_x).digest() == MemoryIndex.rebuild(log_y).digest()
    assert (
        MemoryProjection.rebuild(log_x).digest()
        != MemoryProjection.rebuild(log_y).digest()
    )


# ---------------------------------------------------------------------------
# C. Memory facade
# ---------------------------------------------------------------------------

def test_c1_recall_cannot_distinguish_verified_memory_from_raw_trace(tmp_path):
    """C1 — verification status is lost at the recall boundary.

    A gated, committed memory and an ungated-quality, caller-declared episodic
    trace are returned as identically-shaped `RecalledMemory` records with the
    same score and no tier/verification field, so every consumer (including the
    CLI) can present an unverified trace as an established memory. §84.4
    (verification proportional to impact) and §84.3's two tiers exist precisely
    to distinguish these. Becomes HIGH once M2.2 reranking/consolidation consumes
    `Memory.recall()`.
    """
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="the safe word is umbrella", source="human.creator")
    MemoryTraceWriter(log).record_episodic(
        content="the safe word is umbrella", source="agent.guess"
    )

    hits = Memory(log=log).recall("what is the safe word", limit=5)

    assert len(hits) == 2
    assert "tier" not in hits[0].model_dump()
    assert "verified" not in hits[0].model_dump()
    assert set(hits[0].model_dump()) == {"event_id", "content", "source", "score"}
    assert hits[0].score == hits[1].score  # indistinguishable apart from `source`


def test_c2_get_reports_a_committed_memory_with_empty_payload_as_present(tmp_path):
    """C2 (reconciled via F-M2.1-3) — a falsy-but-present payload stays resolvable
    through `get()`."""
    log = _log(tmp_path)
    log.append(
        Event(
            event_id="01EMPTY000000000000000000AA",
            stream_id="memory",
            event_type="memory.write.committed",
            principal_id="creator",
            payload={},
        )
    )
    memory = Memory(log=log)

    assert "01EMPTY000000000000000000AA" in memory.index.memories  # type: ignore[union-attr]
    assert memory.get("01EMPTY000000000000000000AA") == {}


def test_c3_backend_slots_are_always_materialized(tmp_path):
    """C3 (reconciled via F-M2.1-4) — `_projection`/`_index` slots exist on every
    constructor path (no AttributeError, consistent object shape)."""
    log = _log(tmp_path)
    memory = Memory(index=MemoryIndex.rebuild(log))

    assert hasattr(memory, "_projection")
    assert memory._projection is None
    assert memory.index is not None


def test_c4_invalid_limit_is_rejected_not_silently_truncated(tmp_path):
    """C4 (reconciled) — non-positive or non-int `limit` raises instead of
    silently slicing from the end."""
    log = _log(tmp_path)
    MemoryWriter(log).remember(content="umbrella is a company", source="s")
    MemoryTraceWriter(log).record_episodic(content="safe word umbrella", source="s")

    memory = Memory(log=log)
    assert len(memory.recall("umbrella", limit=3)) == 2
    for bad in (-1, 0, True, 1.5):
        with pytest.raises(ValueError):
            memory.recall("umbrella", limit=bad)


# ---------------------------------------------------------------------------
# D. CLI surface
# ---------------------------------------------------------------------------

def test_d1_cli_recall_multiline_content_collapses_to_one_hit_line(tmp_path, monkeypatch, capsys):
    """D1 (reconciled) — one hit emits exactly one output line; embedded newlines
    are collapsed so `{event_id}  {score:.2f}  [{source}]  {content}` holds."""
    _home(tmp_path, monkeypatch)
    log = EventLog(db_path=str(tmp_path / "log.db"), clock=_FixedClock())
    MemoryTraceWriter(log).record_episodic(
        content="line one\numbrella second line", source="agent.run"
    )
    log.close()

    code = cli.main(["recall", "umbrella"])
    out = capsys.readouterr().out

    assert code == 0
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 1
    assert lines[0].endswith("[agent.run]  line one umbrella second line")


def test_d2_cli_recall_is_offline_with_a_bogus_backend(tmp_path, monkeypatch, capsys):
    """D2 (no-finding) — recall stays offline even with a configured-but-dead
    model backend (port 9 = discard), i.e. it never dials out.
    """
    _home(tmp_path, monkeypatch)
    monkeypatch.setenv("JARVIS_MODEL_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("JARVIS_MODEL_API_KEY", "not-a-real-key")

    log = EventLog(db_path=str(tmp_path / "log.db"), clock=_FixedClock())
    MemoryTraceWriter(log).record_episodic(content="safe word umbrella", source="agent.run")
    log.close()

    code = cli.main(["recall", "umbrella"])
    out = capsys.readouterr().out

    assert code == 0
    assert "umbrella" in out
    assert "no relevant memory" not in out


def test_d3_cli_recall_empty_query_reports_none(tmp_path, monkeypatch, capsys):
    """D3 (no-finding) — an empty query is handled without error and without
    inventing a match.
    """
    _home(tmp_path, monkeypatch)
    log = EventLog(db_path=str(tmp_path / "log.db"), clock=_FixedClock())
    MemoryTraceWriter(log).record_episodic(content="safe word umbrella", source="s")
    log.close()

    code = cli.main(["recall", ""])
    out = capsys.readouterr().out

    assert code == 0
    assert out.strip() == "no relevant memory"
