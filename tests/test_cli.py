from __future__ import annotations

"""Module 11 CLI tests — the §127.1 acceptance sequence, run offline.

Each command is a separate `main()` invocation over the same `JARVIS_HOME`, so
the suite exercises the real restart/replay path.
"""

import pytest

from jarvis import cli
from jarvis.kernel.event_log import EventLog


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    # Keep CLI tests HERMETIC: the machine may have the production model
    # backend configured at user scope; pin the offline deterministic path
    # so test outcomes never depend on a live backend (module 15 M1.1).
    monkeypatch.delenv("JARVIS_MODEL_API_KEY", raising=False)
    monkeypatch.delenv("JARVIS_MODEL_BASE_URL", raising=False)
    return tmp_path


def _run(capsys, *argv: str) -> tuple[int, str]:
    code = cli.main(list(argv))
    return code, capsys.readouterr().out


def _committed_event_id(home) -> str:
    log = EventLog(db_path=str(home / "log.db"))
    try:
        for event in log.replay():
            if event.event_type == "memory.write.committed":
                return event.event_id  # type: ignore[return-value]
    finally:
        log.close()
    raise AssertionError("no committed memory event")


def test_section_127_1_acceptance_sequence(home, capsys):
    code, out = _run(capsys, "init")
    assert code == 0
    assert "creator keypair created (fingerprint: " in out
    assert f"event log initialized at {home / 'log.db'}" in out
    assert "projections initialized" in out
    assert "registry seeded (4 providers)" in out
    assert "core service started" in out
    assert "pairing code: " in out

    code, out = _run(capsys, "say", "remember: the safe word is umbrella")
    assert code == 0
    assert "[thinking]" in out
    assert "memory.write.proposed" in out
    assert "memory.write.verified" in out
    assert "memory.write.committed" in out

    # restart / recovery summary (4 seed + service marker + 3 memory events)
    code, out = _run(capsys)
    assert code == 0
    assert "replayed 8 events" in out
    assert "projections rebuilt" in out
    assert "identity recovered" in out
    assert "last mission: none" in out
    assert "active agents: 0" in out

    code, out = _run(capsys, "say", "what is the safe word?")
    assert code == 0
    assert "umbrella" in out
    assert "source: session 1" in out

    code, out = _run(capsys, "explain", _committed_event_id(home))
    assert code == 0
    assert "cause chain: " in out
    assert out.count(" <- ") == 2  # committed <- verified <- proposed
    assert "memory content: 'the safe word is umbrella'" in out

    code, out = _run(capsys, "replay", "--verify")
    assert code == 0
    assert "verify: OK" in out
    first_hash = next(line for line in out.splitlines() if line.startswith("projection hash:"))

    code, out = _run(capsys, "replay", "--verify")
    second_hash = next(line for line in out.splitlines() if line.startswith("projection hash:"))
    assert first_hash == second_hash


def test_second_init_is_idempotent(home, capsys):
    _run(capsys, "init")
    _run(capsys, "say", "remember: alpha is bravo")
    _, before = _run(capsys)
    count_before = next(
        int(line.split()[1]) for line in before.splitlines() if line.startswith("replayed")
    )

    _run(capsys, "init")
    _, after = _run(capsys)
    count_after = next(
        int(line.split()[1]) for line in after.splitlines() if line.startswith("replayed")
    )

    assert count_before == count_after
    assert count_before == 8  # 4 seed + 1 service marker + 3 memory events


def test_say_question_without_memory_reports_none(home, capsys):
    _run(capsys, "init")
    code, out = _run(capsys, "say", "what is the meaning of life?")
    assert code == 0
    assert "no relevant memory" in out


def test_rejected_memory_reports_rejected(home, capsys):
    _run(capsys, "init")
    code, out = _run(capsys, "say", "remember:")
    assert code == 0
    assert "memory.write.rejected" in out
    assert "memory.write.committed" not in out


def test_explain_unknown_event_fails(home, capsys):
    _run(capsys, "init")
    code, out = _run(capsys, "explain", "01NOSUCHULID0000000000000")
    assert code == 1
    assert "unknown event id" in out


def test_explain_renders_full_blocks_for_memory_event(home, capsys):
    _run(capsys, "init")
    _run(capsys, "say", "remember: the safe word is umbrella")
    code, out = _run(capsys, "explain", _committed_event_id(home))
    assert code == 0
    assert "state transitions: none (no mission events for this stream)" in out
    assert "capability checks: none recorded" in out
    assert "no effects outside manifest" in out
    assert "budget: n/a (no model calls recorded)" in out


def test_model_backed_say_records_question_and_explain_shows_provenance(home, capsys, monkeypatch):
    from jarvis.kernel.model_gateway import ModelGateway
    from jarvis.kernel.registry import CapabilityRegistry

    class FakeAdapter:
        provider_id = "model.adapter"

        async def invoke(self, contract_id, version, args):
            return {"answer": "umbrella", "confidence": 0.9}

        def health_check(self):
            return True

    def fake_gateway(service):
        if service.registry is None:
            return None
        return ModelGateway(
            resolver=service.registry,
            adapters={"model.adapter": FakeAdapter()},
        )

    _run(capsys, "init")
    _run(capsys, "say", "remember: the safe word is umbrella")

    monkeypatch.setattr(cli, "_build_model_gateway", fake_gateway)
    code, out = _run(capsys, "say", "what is the safe word?")
    assert code == 0
    assert "umbrella" in out
    assert "model-grounded" in out
    assert "provider: model.adapter" in out

    log = EventLog(db_path=str(home / "log.db"))
    try:
        asked = [e for e in log.replay() if e.event_type == "question.asked"]
    finally:
        log.close()
    assert len(asked) == 1
    assert asked[0].payload["fallback"] == "model"

    code, out = _run(capsys, "explain", asked[0].event_id)
    assert code == 0
    assert "answer path: model" in out
    assert "model: model.adapter (model.generate_structured@1.0.0)" in out
    assert "retrieved memories: 1 (top score" in out
    assert "budget: 1 model call(s)" in out


def test_cli_recall_searches_memories_and_traces(home, capsys):
    from jarvis.kernel.event_log import EventLog
    from jarvis.kernel.memory_trace import MemoryTraceWriter

    _run(capsys, "init")
    _run(capsys, "say", "remember: the safe word is umbrella")

    log = EventLog(db_path=str(home / "log.db"))
    try:
        MemoryTraceWriter(log).record_episodic(
            content="session began with an umbrella handoff",
            source="agent.run",
        )
    finally:
        log.close()

    code, out = _run(capsys, "recall", "umbrella")
    assert code == 0
    assert "[agent.run]  session began with an umbrella handoff" in out
    assert "[session 1]  the safe word is umbrella" in out


def test_cli_recall_with_no_matches_reports_none(home, capsys):
    _run(capsys, "init")
    code, out = _run(capsys, "recall", "quantum entanglement")
    assert code == 0
    assert "no relevant memory" in out
