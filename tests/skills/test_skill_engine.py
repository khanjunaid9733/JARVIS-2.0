from __future__ import annotations

import tempfile
from pathlib import Path
from jarvis.skills.admission import SkillAdmissionPolicy
from jarvis.skills.context import SkillExecutionContext
from jarvis.skills.dispatcher import SkillDispatcher
from jarvis.skills.engine import SkillGoalResult, SkillRuntimeEngine
from jarvis.skills.health import SkillHealthChecker
from jarvis.skills.manifest import (
    SkillManifest,
    SkillPrerequisites,
    SkillWorkflowStep,
    parse_skill_markdown,
)
from jarvis.skills.registry import SkillRegistry


def _admit(*skill_ids: str) -> SkillAdmissionPolicy:
    """Execution is default-deny (ADR-011 S4); these tests state what they run."""
    return SkillAdmissionPolicy(entries=frozenset(skill_ids))


def _make_mock_skill(
    skill_id: str,
    domain: str = "tools",
    code: str = "print('engine-ok')",
    binaries: list[str] | None = None,
) -> SkillManifest:
    return SkillManifest(
        id=skill_id,
        name=skill_id,
        domain=domain,
        title=f"Mock {skill_id}",
        description=f"Skill for {skill_id} operations and testing",
        triggers=[f"run {skill_id}", f"do {skill_id}"],
        prerequisites=SkillPrerequisites(required_binaries=binaries or []),
        workflow_steps=[SkillWorkflowStep(step_index=1, language="python", code=code)],
    )


def test_engine_exact_match_resolution():
    reg = SkillRegistry()
    skill = _make_mock_skill("dev-git-sync")
    reg.register(skill)

    engine = SkillRuntimeEngine(registry=reg)
    resolved, matches = engine.resolve_skill("dev-git-sync")
    assert resolved is not None
    assert resolved.id == "dev-git-sync"
    assert len(matches) == 1


def test_engine_semantic_intent_resolution():
    reg = SkillRegistry()
    skill = _make_mock_skill("netadmin-backup-db", domain="database")
    reg.register(skill)

    engine = SkillRuntimeEngine(registry=reg)
    resolved, matches = engine.resolve_skill("backup db database")
    assert resolved is not None
    assert resolved.id == "netadmin-backup-db"


def test_engine_no_match_returns_clean_result(tmp_path: Path):
    reg = SkillRegistry()
    engine = SkillRuntimeEngine(registry=reg)
    ctx = SkillExecutionContext(workspace=tmp_path)

    res = engine.execute_goal("nonexistent rocket launch xyz", ctx)
    assert res.success is False
    assert res.status == "NO_MATCH"
    assert res.selected_skill is None
    assert "No matching skill" in res.message


def test_engine_unhealthy_skill_is_refused(tmp_path: Path):
    reg = SkillRegistry()
    unhealthy_skill = _make_mock_skill(
        "cloud-deploy-k8s",
        binaries=["totally_nonexistent_cli_xyz_12345"],
    )
    reg.register(unhealthy_skill)

    engine = SkillRuntimeEngine(registry=reg, admission=_admit("cloud-deploy-k8s"))
    ctx = SkillExecutionContext(workspace=tmp_path, dry_run=False)

    res = engine.execute_goal("cloud-deploy-k8s", ctx)
    assert res.success is False
    assert res.status == "REFUSED"
    assert res.health is not None
    assert not res.health.is_executable
    assert "missing binaries" in res.message


def test_engine_dry_run_execution(tmp_path: Path):
    reg = SkillRegistry()
    skill = _make_mock_skill("cloud-deploy-k8s", binaries=["nonexistent_bin"])
    reg.register(skill)

    engine = SkillRuntimeEngine(registry=reg, admission=_admit("cloud-deploy-k8s"))
    ctx = SkillExecutionContext(workspace=tmp_path, dry_run=True)

    res = engine.execute_goal("cloud-deploy-k8s", ctx)
    assert res.success is True
    assert res.status == "SUCCEEDED"
    assert res.execution is not None
    assert res.execution.success is True


def test_engine_successful_execution(tmp_path: Path):
    reg = SkillRegistry()
    skill = _make_mock_skill("media-audio-verify", code="print('AUDIO_SUCCESS')")
    reg.register(skill)

    engine = SkillRuntimeEngine(registry=reg, admission=_admit("media-audio-verify"))
    ctx = SkillExecutionContext(workspace=tmp_path)

    res = engine.execute_goal("media-audio-verify", ctx)
    assert res.success is True
    assert res.status == "SUCCEEDED"
    assert res.execution is not None
    assert "AUDIO_SUCCESS" in res.execution.stdout
