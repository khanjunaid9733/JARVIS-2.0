"""ADR-011 S0/S2 regression tests.

Guards two invariants, both of which were broken before ADR-011:

S0  No caller may call `EventLog.append` with bare keyword arguments. The
    signature is `append(event: Event | Mapping)`, so `append(stream_id=...)`
    raises `TypeError`. Ten call sites did that, each wrapped in
    `except Exception: pass`, so every audit event they intended to write was
    silently discarded. `EventLog.audit` is the supported keyword form.

S2  Learning is a FILE WRITE, not a capability. An earlier revision of this
    ADR gated `learn_skill` behind an Ed25519 `skill_learn` grant. That gate was
    theater and was removed, because the agent already holds
    `run_system_command` and `filesystem_operation`:

      * `filesystem_operation` can write `.agents/skills/<n>/SKILL.md` directly,
        bypassing `learn_skill` entirely;
      * `run_system_command` can shell out to the grant-minting command, which
        signs with the creator key sitting in the agent's own `$JARVIS_HOME`.

    A signature over a payload the subject can produce at will proves nothing
    about who authorized it. The boundary that actually holds is S4: a skill is
    inert until a human admits it to the execution allowlist, and that check
    runs at dispatch against the file rather than against its provenance. These
    tests pin that real boundary, and record the digest as an audit artifact.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from jarvis.kernel.event_log import EventLog
from jarvis.skills.admission import DEFAULT_ENV_VAR, load_policy
from jarvis.skills.cognitive_agent import CognitiveAgent

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "jarvis"

# Files that legitimately construct an append argument. Everything else must
# use `audit(...)` instead of kwargs-style `append(...)`.
ALLOWED_APPEND_CALLERS = {
    SRC_ROOT / "kernel" / "event_log.py",  # the definition itself
}


def _iter_append_call_sites() -> list[tuple[Path, int]]:
    """Return (file, lineno) for every `.append(...)` call in the source tree."""
    sites: list[tuple[Path, int]] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        if path in ALLOWED_APPEND_CALLERS:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr != "append":
                continue
            if node.keywords:
                sites.append((path, node.lineno))
    return sites


def test_no_kwarg_style_event_log_append_calls() -> None:
    """S0: kwargs-style `.append(...)` raises TypeError at runtime.

    A single remaining call site is a silently-dropped audit event, so this is
    asserted structurally over the whole source tree rather than per-module.
    """
    offenders = [
        f"{path.relative_to(SRC_ROOT)}:{lineno}" for path, lineno in _iter_append_call_sites()
    ]
    assert not offenders, (
        "kwargs-style .append() calls found (each is a TypeError that has "
        f"previously been swallowed): {offenders}. Use EventLog.audit(...)."
    )


def test_audit_helper_writes_a_real_event(tmp_path: Path) -> None:
    log = _log(tmp_path)
    try:
        event_id = log.audit(
            stream_id="skills",
            event_type="skill.learned",
            principal_id="cognitive_agent",
            payload={"skill_id": "demo"},
        )
        assert event_id
        types = [e.event_type for e in log.replay()]
        assert "skill.learned" in types
        assert log.verify_chain()
    finally:
        log.close()


def test_audit_helper_does_not_swallow_failures(tmp_path: Path) -> None:
    """A closed log must raise, not silently drop the audit record."""
    log = _log(tmp_path)
    log.close()
    with pytest.raises(Exception):
        log.audit(
            stream_id="skills",
            event_type="skill.learned",
            principal_id="cognitive_agent",
            payload={"skill_id": "demo"},
        )


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch) -> None:
    """Point JARVIS_HOME at this test's own tmp dir.

    The default log and the skills dir both resolve from ambient state, so
    without this the tests would share a log and see each other's skills.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("JARVIS_HOME", str(home))


def _log(tmp_path: Path) -> EventLog:
    """Isolated event log per test.

    The default log lives at `$JARVIS_HOME/log.db`; without an explicit
    `db_path` these tests would share one log and see each other's events.
    """
    return EventLog(db_path=str(tmp_path / "log.db"))


def _code_digest(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()




def _code_digest(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def test_learn_writes_file_and_journals_digest(tmp_path: Path, monkeypatch) -> None:
    """S2: learning writes a file and records WHAT landed, with no grant needed.

    The result must state plainly that the skill is not executable yet.
    """
    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.chdir(workdir)

    code = "Write-Output hello"
    log = _log(tmp_path)
    try:
        agent = CognitiveAgent(event_log=log)
        out, ok = agent.execute_tool(
            "learn_skill", {"skill_name": "demo", "code": code, "description": "d"}
        )
        assert ok is True
        assert out["skill_id"] == "demo"
        assert (workdir / ".agents" / "skills" / "demo" / "SKILL.md").exists()

        # The result must not imply the skill is now runnable.
        assert out["executable"] is False
        assert "jarvis skill admit demo" in out["next_step"]

        learned = [e for e in log.replay() if e.event_type == "skill.learned"]
        assert len(learned) == 1
        assert learned[0].payload["code_sha256"] == _code_digest(code)
        assert learned[0].payload["executable"] is False
        assert log.verify_chain()
    finally:
        log.close()


def test_learned_skill_is_not_executable_until_admitted(tmp_path: Path, monkeypatch) -> None:
    """The real S2 boundary: a written skill stays inert under the S4 allowlist.

    This is the invariant that replaces the grant. Learning succeeds, and the
    skill is still refused at execution time until a human admits it.
    """
    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.chdir(workdir)

    code = "Write-Output hello"
    log = _log(tmp_path)
    try:
        agent = CognitiveAgent(event_log=log)
        out, ok = agent.execute_tool(
            "learn_skill", {"skill_name": "demo", "code": code, "description": "d"}
        )
        assert ok is True
        assert out["executable"] is False

        # The effective default policy admits only the hand-reviewed seeds, so
        # the freshly learned skill cannot run.
        assert load_policy(env={}).is_admitted("demo") is False

        # Only after an explicit human admission does it become runnable.
        assert load_policy(env={DEFAULT_ENV_VAR: "demo"}).is_admitted("demo") is True
    finally:
        log.close()


def test_skill_written_by_a_tool_is_also_inert(tmp_path: Path, monkeypatch) -> None:
    """Bypassing `learn_skill` must not buy execution.

    The agent can write `.agents/skills/<n>/SKILL.md` with
    `filesystem_operation`, skipping learning entirely. S4 is evaluated at
    dispatch against the file, not its provenance, so the shortcut gains nothing.
    """
    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.chdir(workdir)

    md = (
        "---\nname: smuggled\ndescription: written straight to disk\n---\n\n"
        "# W\n\n## Workflow\n\n```powershell\nWrite-Output OWNED\n```\n"
    )
    out, ok = CognitiveAgent(event_log=None).execute_tool(
        "filesystem_operation",
        {"operation": "write_file", "path": str(workdir / ".agents/skills/smuggled/SKILL.md"), "content": md},
    )
    assert ok is True
    assert (workdir / ".agents" / "skills" / "smuggled" / "SKILL.md").exists()

    # Present on disk, but absent from the allowlist => not runnable.
    assert load_policy(env={}).is_admitted("smuggled") is False


def test_learn_never_asserts_execution_rights(tmp_path: Path, monkeypatch) -> None:
    """A successful learn must not report the skill as runnable.

    Guards the reply text: the old wording implied the skill could now run.
    """
    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.chdir(workdir)

    log = _log(tmp_path)
    try:
        agent = CognitiveAgent(event_log=log)
        result = agent.process_turn("learn: smoke hello | Write-Output hi | a test", source="cli")
        assert result.action == "skill_learned"
        assert "not executable" in result.reply.lower()
        assert "admit" in result.reply
    finally:
        log.close()


def test_empty_code_is_refused(tmp_path: Path, monkeypatch) -> None:
    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.chdir(workdir)

    log = _log(tmp_path)
    try:
        agent = CognitiveAgent(event_log=log)
        out, ok = agent.execute_tool("learn_skill", {"skill_name": "demo", "code": "   "})
        assert ok is False
        assert "empty code" in out["error"]
        assert not (workdir / ".agents" / "skills" / "demo" / "SKILL.md").exists()
    finally:
        log.close()


def test_grant_gate_removed_from_creator_action_types() -> None:
    """The ceremonial `skill_learn` action type must not linger in the kernel.

    It implied a cryptographic guarantee that never existed.
    """
    from jarvis.kernel.crypto_authority import CreatorActionType

    assert "SKILL_LEARN" not in CreatorActionType.__members__
