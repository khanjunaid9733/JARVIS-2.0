from __future__ import annotations

"""Live loop tests (composition root: `jarvis.live` + `jarvis mission` / `jarvis voice`).

These exercise the REAL entry point (`jarvis.cli.main`) over a clean
`JARVIS_HOME`, so they assert behaviour the user can reproduce on the command
line - not claims about the modules.

Hermetic by construction: no model backend, no transcription engine, no
network. The one place a real engine could reach out (`--audio`) is covered by
stubbing the resolver to a *seam* and asserting the turn refuses to fabricate
a transcript.
"""

import hashlib
import json

import pytest

from jarvis import cli
from jarvis.kernel.event_log import EventLog
from jarvis.kernel.memory_api import Memory
from jarvis.live import LiveRuntime


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    for name in (
        "JARVIS_MODEL_API_KEY",
        "JARVIS_MODEL_BASE_URL",
        "JARVIS_MODEL_NAME",
        "JARVIS_STT_CMD",
        "JARVIS_TTS_CMD",
    ):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def _run(capsys, *argv: str) -> tuple[int, str]:
    code = cli.main(list(argv))
    return code, capsys.readouterr().out


def _events(home) -> list:
    log = EventLog(db_path=str(home / "log.db"))
    try:
        return list(log.replay())
    finally:
        log.close()


# ---------------------------------------------------------------------------
# the goal: intake -> decompose -> dispatch -> verify -> recover -> recall
# ---------------------------------------------------------------------------


def test_mission_runs_end_to_end_and_verifies_its_artifacts_on_disk(home, capsys):
    assert _run(capsys, "init")[0] == 0
    code, out = _run(capsys, "mission", "make the boot path deterministic")
    assert code == 0

    assert "intake: mission mission-" in out
    assert "decompose: plan -> deliver -> attest" in out
    assert "router: implementation.v1 -> bigpickle" in out
    assert "step plan: attempt 1 -> verified" in out
    assert "completion: gate PASSED -> task.completed" in out
    assert "outcome=ACCEPTED lifecycle=completed" in out
    assert "hash chain OK" in out
    assert "recall: memory committed; 1 hit(s)" in out

    # the artifacts are real bytes and verify independently on disk
    artifacts = sorted((home / "workspace" / "artifacts").iterdir())
    deliverable = next(p for p in artifacts if p.suffix == ".json")
    sidecar = next(p for p in artifacts if p.name.endswith(".json.sha256"))
    body = json.loads(deliverable.read_text(encoding="utf-8"))
    assert body["goal"] == "make the boot path deterministic"
    assert body["goal_sha256"] == hashlib.sha256(b"make the boot path deterministic").hexdigest()
    assert json.loads(sidecar.read_text(encoding="utf-8"))["sha256"] == (
        hashlib.sha256(deliverable.read_bytes()).hexdigest()
    )
    assert (home / "workspace" / "work_orders").is_dir()

    # the mission really completed through the NAT-05 gate
    types = [event.event_type for event in _events(home)]
    assert "task.completed" in types
    assert "task.completion_refused" not in types
    assert types.count("effect.verified") == 3


def test_declared_fault_is_repaired_by_the_real_recovery_ladder(home, capsys):
    assert _run(capsys, "init")[0] == 0
    code, out = _run(capsys, "mission", "repair the boot path", "--fault", "deliver=1")
    assert code == 0

    assert "step deliver: attempt 1 -> FAILED" in out
    assert "recovery retry" in out
    assert "step deliver: attempt 2 -> verified; retry context carried" in out
    assert "recover: 1 ladder action(s) materialized (retry on deliver)" in out
    assert "outcome=ACCEPTED" in out

    # the worker really received the failure bytes on the retry attempt
    deliverable = next((home / "workspace" / "artifacts").glob("mission-*.json"))
    body = json.loads(deliverable.read_text(encoding="utf-8"))
    assert body["attempt"] == 2
    assert body["recovered"] is True
    assert "[recovery] previous attempt #1 for step deliver failed" in body["recovery_context"]

    # only the repaired attempt wrote: the faulted attempt ran no effect at all
    types = [e.event_type for e in _events(home)]
    assert types.count("effect.verified") == 3
    assert types.count("effect.prepared") == 3


def test_mission_halts_and_refuses_completion_when_repair_is_exhausted(home, capsys):
    assert _run(capsys, "init")[0] == 0
    code, out = _run(capsys, "mission", "an unachievable goal", "--fault", "deliver=99")
    assert code == 0

    assert "step deliver: attempt 3 -> FAILED" in out
    assert "completion: gate REFUSED -> task.completion_refused" in out
    assert "outcome=HELD" in out
    assert "lifecycle=refused" in out

    types = [event.event_type for event in _events(home)]
    assert "task.completion_refused" in types
    assert "task.completed" not in types
    # the mission never reached a frozen success
    assert "frozen_success" not in out


def test_live_loop_never_registers_providers_into_the_durable_log(home, capsys):
    """The live catalog is in-memory: the §127.1 '4 providers' invariant holds."""
    assert _run(capsys, "init")[0] == 0
    _, out = _run(capsys, "mission", "keep the registry frozen")
    added = [e for e in _events(home) if e.event_type == "capability.provider_added"]
    assert len(added) == 4
    assert "4 seeded providers" in out


def test_dispatch_traces_are_real_records_the_daemon_adjudicates(home, capsys):
    assert _run(capsys, "init")[0] == 0
    code, out = _run(capsys, "mission", "record the dispatch plane")
    assert code == 0

    records = [
        json.loads(line)
        for line in (home / "dispatches.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    per_step = {record["step_id"] for record in records}
    assert per_step == {"plan", "deliver", "attest"}
    assert all(
        {r["event"] for r in records if r["step_id"] == step}
        == {"DISPATCH_INTENT", "DISPATCH_STARTED", "DISPATCH_COMPLETED"}
        for step in per_step
    )
    # SupervisorDaemon folded those records and the mission lease for real
    assert "dispatch-plan:normal" in out
    assert "dispatch-deliver:normal" in out
    assert "leases [lease-" in out and ":fresh]" in out


# ---------------------------------------------------------------------------
# the voice turn
# ---------------------------------------------------------------------------


def test_voice_turn_answers_from_memory_and_journals_the_fsm(home, capsys):
    assert _run(capsys, "init")[0] == 0
    assert _run(capsys, "say", "remember: the deploy gate runs on Thursdays")[0] == 0
    code, out = _run(capsys, "voice", "when does the deploy gate run")
    assert code == 0

    assert "answer: 'the deploy gate runs on Thursdays'" in out
    assert (
        "voice loop: real 6-state turn-taking FSM; transitions journaled on stream "
        "'voice-session' (listening -> user_speaking -> thinking -> assistant_speaking -> listening)"
    ) in out
    assert "hash chain OK" in out

    transitions = [
        e for e in _events(home) if e.event_type == "multimodal.voice_state_changed"
    ]
    assert [e.payload["to_state"] for e in transitions] == [
        "listening",
        "user_speaking",
        "thinking",
        "assistant_speaking",
        "listening",
    ]


def test_voice_turn_names_a_seam_instead_of_fabricating_perception(home, monkeypatch):
    """With no STT engine bound the turn must say so - never emit a mock transcript."""
    monkeypatch.setattr(
        "jarvis.live._resolve_stt_engine", lambda: (None, "seam - no engine bound")
    )
    monkeypatch.setattr(
        "jarvis.live._resolve_tts_engine", lambda: (None, "seam - no engine bound")
    )
    cli.main(["init"])
    service = cli.CoreService()
    service.start()
    try:
        runtime = LiveRuntime(service)
        assert runtime.stt is None and runtime.tts is None
        spoken = runtime.voice_turn(
            "typed turn", audio=home / "not-audio.wav"
        )
    finally:
        service.close()

    assert spoken.stt == "seam - no engine bound"
    assert spoken.transcript_source == "typed utterance"
    assert spoken.utterance == "typed turn"  # not a fabricated transcript
    assert any("was NOT transcribed" in line for line in spoken.lines)
    assert any("no mock transcript is fabricated" in line for line in spoken.lines)
    assert any(line == "tts: skipped - nothing to speak (seam - no engine bound)" for line in spoken.lines)


def test_tts_command_seam_writes_real_audio_bytes_when_an_engine_is_bound(home, monkeypatch):
    """The TTS seam is real plumbing: a bound engine's bytes reach disk.

    The bound engine is a real process writing a real, non-silent WAV, and the
    turn re-measures that payload before it counts (a copy of the text file, or
    a WAV of pure silence, is reported as a FAILED synthesis). This proves the
    WIRING; whether THIS machine has a synthesis engine of its own is pinned by
    `tests/test_live_voice.py`.
    """
    monkeypatch.setenv(
        "JARVIS_TTS_CMD",
        'python -c "'
        "import struct,sys,wave;"
        "h=wave.open(sys.argv[2],'wb');h.setnchannels(1);h.setsampwidth(2);h.setframerate(22050);"
        "h.writeframes(struct.pack('<22050h',*([9000]*22050)));h.close()"
        '"',
    )
    monkeypatch.setattr(
        "jarvis.live._resolve_stt_engine", lambda: (None, "seam - no engine bound")
    )
    cli.main(["init"])
    cli.main(["say", "remember: the deploy gate runs on Thursdays"])
    service = cli.CoreService()
    service.start()
    try:
        runtime = LiveRuntime(service)
        spoken = runtime.voice_turn("when does the deploy gate run")
    finally:
        service.close()

    assert spoken.answered is True
    assert spoken.audio_out is not None
    audio = home / "audio"
    assert list(audio.iterdir())  # real bytes on disk, not a mock string
    assert any(line.startswith("tts: real - JARVIS_TTS_CMD=") for line in spoken.lines)


def test_recall_survives_a_mission_and_a_voice_turn(home, capsys):
    assert _run(capsys, "init")[0] == 0
    assert _run(capsys, "mission", "index the audit trail")[0] == 0
    assert _run(capsys, "voice", "what did the mission do")[0] == 0

    log = EventLog(db_path=str(home / "log.db"))
    try:
        assert log.verify_chain() is True
        hits = Memory(log=log).recall("index the audit trail", limit=3)
    finally:
        log.close()
    assert hits and "index the audit trail" in hits[0].content
