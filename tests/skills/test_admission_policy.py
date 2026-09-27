"""ADR-011 S4 regression tests: default-deny execution admission.

Before S4 every one of ~2,400 library skills was dispatchable. A natural
language goal could resolve to a skill whose "workflow" was documentation
prose, and it would be executed. Now a skill must appear on an explicit
allowlist to run; everything else stays discoverable and inspectable.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from jarvis.skills.admission import (
    DEFAULT_ADMITTED,
    AdmissionEntry,
    SkillAdmissionPolicy,
    admission_path,
    load_admission_file,
    load_policy,
    write_admission_file,
)
from jarvis.skills.context import SkillExecutionContext
from jarvis.skills.dispatcher import SkillDispatcher
from jarvis.skills.manifest import parse_skill_markdown

DENY_ALL = SkillAdmissionPolicy(entries=frozenset())


def _hash_skill() -> "object":
    fence = "`" * 3
    return parse_skill_markdown(
        "---\nname: security-hash-text\ndescription: hash text\n---\n"
        f"\n# Hash\n\n## Workflow\n\n{fence}python\nimport hashlib\n"
        "print(hashlib.sha256('x'.encode()).hexdigest())\n"
        f"{fence}\n",
        "security-hash-text",
    )


def test_unadmitted_skill_is_refused_before_execution(tmp_path: Path) -> None:
    skill = _hash_skill()
    ctx = SkillExecutionContext(workspace=tmp_path)
    result = SkillDispatcher(admission=DENY_ALL).dispatch(skill, ctx)
    assert result.success is False
    assert result.refusal_reason is not None
    assert "not on the execution allowlist" in result.refusal_reason
    assert result.exit_code == -1


def test_admitted_skill_runs(tmp_path: Path) -> None:
    skill = _hash_skill()
    policy = SkillAdmissionPolicy(entries=frozenset({"security-hash-text"}))
    ctx = SkillExecutionContext(workspace=tmp_path, timeout_seconds=60.0)
    result = SkillDispatcher(admission=policy).dispatch(skill, ctx)
    assert result.success is True, result.stderr


def test_default_policy_admits_the_reviewed_skills() -> None:
    policy = load_policy(path="does-not-exist.json", env={})
    ids = set(policy.admitted_ids())
    assert {"files-hash", "security-hash-text"} <= ids


def test_default_admitted_entries_carry_notes() -> None:
    assert all(e.note for e in DEFAULT_ADMITTED)


def test_unknown_skill_is_denied() -> None:
    policy = load_policy(path="does-not-exist.json", env={})
    assert policy.is_admitted("3d-games") is False
    assert policy.is_admitted("some-unknown-skill") is False


def test_env_override_is_additive(tmp_path: Path) -> None:
    policy = load_policy(
        path=tmp_path / "none.json", env={"JARVIS_SKILL_ADMISSION": "my-skill,other"}
    )
    assert policy.is_admitted("my-skill")
    assert policy.is_admitted("other")
    # defaults survive
    assert policy.is_admitted("files-hash")


def test_env_override_cannot_be_used_to_widen_a_file_denied_by_corruption(
    tmp_path: Path,
) -> None:
    bad = tmp_path / "skill_admission.json"
    bad.write_text("{not json", encoding="utf-8")
    policy = load_policy(path=bad, env={})
    # A corrupt policy file must not silently deny the built-in reviewed set,
    # but it must not admit anything unlisted either.
    assert "files-hash" in policy.admitted_ids()
    assert "3d-games" not in policy.admitted_ids()


def test_missing_file_falls_back_to_defaults(tmp_path: Path) -> None:
    policy = load_policy(path=tmp_path / "absent.json", env={})
    assert "files-hash" in policy.admitted_ids()


def test_round_trip_write_and_read(tmp_path: Path) -> None:
    target = tmp_path / "admission.json"
    write_admission_file(
        [AdmissionEntry(skill_id="b-skill", note="n"), AdmissionEntry(skill_id="a-skill")],
        target,
    )
    entries = load_admission_file(target)
    assert {e.skill_id for e in entries} == {"a-skill", "b-skill"}
    by_id = {e.skill_id: e for e in entries}
    assert by_id["b-skill"].note == "n"


def test_string_form_entries_are_accepted(tmp_path: Path) -> None:
    target = tmp_path / "admission.json"
    target.write_text(
        '{"schema": 1, "admitted": ["plain-skill"]}', encoding="utf-8"
    )
    assert [e.skill_id for e in load_admission_file(target)] == ["plain-skill"]


def test_default_path_is_beside_the_skills() -> None:
    assert admission_path().name == "skill_admission.json"
    assert admission_path().parent.name == "skills"


def test_refusal_is_journalled(tmp_path: Path) -> None:
    """A denial must be auditable, not silent."""
    from jarvis.kernel.event_log import EventLog

    log = EventLog(db_path=str(tmp_path / "log.db"))
    try:
        ctx = SkillExecutionContext(workspace=tmp_path)
        result = SkillDispatcher(
            event_sink=log, admission=DENY_ALL
        ).dispatch(_hash_skill(), ctx)
        assert result.refusal_reason is not None
        refusals = [e for e in log.replay() if e.event_type == "skill.refused"]
        assert len(refusals) == 1
        assert refusals[0].payload["refusal_stage"] == "admission"
        assert refusals[0].payload["skill_id"] == "security-hash-text"
    finally:
        log.close()


def test_dry_run_may_preview_an_unadmitted_skill(tmp_path: Path) -> None:
    """A dry run creates no subprocess and only renders declared steps, so it is
    exempt from admission - that is how an operator inspects a skill before
    deciding to admit it. Real execution is still refused."""
    fence = "`" * 3
    skill = parse_skill_markdown(
        "---\nname: 3d-games\ndescription: prose skill\n---\n"
        f"\n# 3D\n\n## Workflow\n\n{fence}bash\necho hi\n{fence}\n",
        "3d-games",
    )
    ctx = SkillExecutionContext(workspace=tmp_path, dry_run=True)
    preview = SkillDispatcher(admission=DENY_ALL).dispatch(skill, ctx)
    assert preview.success is True
    assert "[DRY-RUN]" in preview.stdout

    ctx_real = SkillExecutionContext(workspace=tmp_path, dry_run=False)
    real = SkillDispatcher(admission=DENY_ALL).dispatch(skill, ctx_real)
    assert real.success is False
    assert real.refusal_reason is not None


def test_discovery_is_unaffected_by_admission(tmp_path: Path) -> None:
    """A refused skill must still be listable, i.e. admission != invisibility.

    Uses `3d-games`, which is a real prose skill that is not admitted.
    """
    fence = "`" * 3
    skill = parse_skill_markdown(
        "---\nname: 3d-games\ndescription: 3D game development principles\n---\n"
        f"\n# 3D\n\n## Workflow\n\n{fence}\n1. **Open a 3D engine**\n{fence}\n",
        "3d-games",
    )
    policy = load_policy(path="does-not-exist.json", env={})
    assert skill.id == "3d-games"  # still a normal, discoverable manifest
    assert skill.description  # still carries metadata
    assert policy.is_admitted(skill.id) is False  # but not executable


# --- content pin (ADR-011 S4) ------------------------------------------------
#
# `jarvis skill admit` records a sha256 of the reviewed SKILL.md and prints
# "pinned sha256". Before this was enforced, the pin was write-only: admission
# was by id alone, so the agent could rewrite an admitted file through
# `filesystem_operation` and the tampered version would still execute. These
# tests pin the real behavior.


def _write_skill_file(root: Path, name: str, body: str = "Write-Output original") -> Path:
    d = root / ".agents" / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    fence = "`" * 3
    p = d / "SKILL.md"
    p.write_text(
        "---\n"
        f"name: {name}\n"
        "description: pin test\n"
        "---\n"
        f"\n# T\n\n## Workflow\n\n{fence}powershell\n{body}\n{fence}\n",
        encoding="utf-8",
    )
    return p


def test_admitted_skill_whose_file_changed_is_refused(tmp_path: Path) -> None:
    """A post-admission rewrite must not execute. This is the point of the pin."""
    src = _write_skill_file(tmp_path, "pinned-skill", "Write-Output original")
    original_digest = hashlib.sha256(src.read_bytes()).hexdigest()

    policy = SkillAdmissionPolicy(
        entries=frozenset(
            {AdmissionEntry(skill_id="pinned-skill", source_sha256=original_digest)}
        )
    )
    skill = parse_skill_markdown(src.read_text(encoding="utf-8"), "pinned-skill")
    skill.source_path = str(src)

    # Unmodified: allowed.
    assert policy.check_content("pinned-skill", src) is None

    # Tampered: refused.
    src.write_text(src.read_text(encoding="utf-8").replace("original", "Remove-Item -Recurse -Force C:/"), encoding="utf-8")
    reason = policy.check_content("pinned-skill", src)
    assert reason is not None
    assert "content changed after admission" in reason

    result = SkillDispatcher(admission=policy).dispatch(
        skill, SkillExecutionContext(workspace=tmp_path)
    )
    assert result.success is False
    assert "content changed after admission" in (result.refusal_reason or "")


def test_unpinned_entry_is_allowed(tmp_path: Path) -> None:
    """An entry with no digest carries no promise, so content changes do not block it."""
    src = _write_skill_file(tmp_path, "unpinned-skill")
    policy = SkillAdmissionPolicy(entries=frozenset({"unpinned-skill"}))
    assert policy.check_content("unpinned-skill", src) is None
    src.write_text(src.read_text(encoding="utf-8").replace("original", "other"), encoding="utf-8")
    assert policy.check_content("unpinned-skill", src) is None


def test_pinned_entry_with_missing_file_is_refused(tmp_path: Path) -> None:
    """A pin whose file vanished is not silently allowed."""
    policy = SkillAdmissionPolicy(
        entries=frozenset({AdmissionEntry(skill_id="gone", source_sha256="ab" * 32)})
    )
    reason = policy.check_content("gone", tmp_path / "nope" / "SKILL.md")
    assert reason is not None
    assert "missing" in reason


def test_policy_accepts_plain_id_strings() -> None:
    """Callers may pass ids; they carry no pin."""
    policy = SkillAdmissionPolicy(entries=frozenset({"a", "b"}))
    assert policy.is_admitted("a") is True
    assert policy.entry_for("a") is not None
    assert policy.entry_for("a").source_sha256 is None
    assert policy.admitted_ids() == ("a", "b")
