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
