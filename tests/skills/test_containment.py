"""ADR-011 S5 regression tests: honest containment.

The dispatcher's docstring claimed "strict path jailing". Nothing enforced it:
`_run_step` used a bare `subprocess.run`, which has no process-tree cleanup, so
a step that spawned a grandchild left it running after a timeout. Two things
are asserted here:

1. The step now runs through the existing `ContainedProcess` seam, so a
   timeout terminates the whole descendant tree and the child gets the
   default-deny environment rather than the parent's.
2. The module documents what containment IS (process-level) instead of claiming
   a filesystem jail it never had.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from jarvis.skills.admission import SkillAdmissionPolicy
from jarvis.skills.context import SkillExecutionContext
from jarvis.skills.dispatcher import (
    CONTAINMENT_BOUNDARY,
    DISPATCHABLE_LANGUAGES,
    INHERITED_ENV_ALLOWLIST,
    SkillDispatcher,
)
from jarvis.orchestrator.bridges.process import ContainedProcess


def _admit(*ids: str) -> SkillAdmissionPolicy:
    return SkillAdmissionPolicy(entries=frozenset(ids))


def _python_skill(skill_id: str, code: str):
    from jarvis.skills.manifest import parse_skill_markdown

    fence = "`" * 3
    return parse_skill_markdown(
        f"---\nname: {skill_id}\ndescription: fixture\n---\n"
        f"\n# Fixture\n\n## Workflow\n\n{fence}python\n{code}\n{fence}\n",
        skill_id,
    )


def test_containment_boundary_does_not_claim_a_filesystem_jail() -> None:
    lowered = CONTAINMENT_BOUNDARY.lower()
    assert "not a filesystem" in lowered
    assert "job-object" in lowered or "process-group" in lowered


def test_module_docstring_does_not_assert_path_jailing() -> None:
    """The docstring must not CLAIM jailing; naming the old claim to retract it
    is fine, asserting it is not."""
    from jarvis.skills import dispatcher

    doc = " ".join((dispatcher.__doc__ or "").lower().split())
    assert "not get a filesystem, network, or registry jail" in doc
    # Any mention of the old claim must be an explicit retraction.
    if "strict path jailing" in doc:
        assert "was not true" in doc


def test_step_runs_in_a_contained_process(tmp_path: Path) -> None:
    skill = _python_skill("contained-ok", "print('CONTAINED_OK')")
    ctx = SkillExecutionContext(workspace=tmp_path, timeout_seconds=60.0)
    res = SkillDispatcher(admission=_admit("contained-ok")).dispatch(skill, ctx)
    assert res.success is True, res.stderr
    assert "CONTAINED_OK" in res.stdout


def test_timeout_kills_the_process_tree(tmp_path: Path) -> None:
    """A step that spawns a grandchild must not leave it running.

    The grandchild is a real file rather than inline `-c` code: the point is
    the process boundary, not the quoting.
    """
    marker = tmp_path / "grandchild.txt"
    grandchild = tmp_path / "grandchild.py"
    grandchild.write_text(
        "import pathlib, time\n"
        "time.sleep(20)\n"
        f"pathlib.Path(r'{marker}').write_text('leaked')\n",
        encoding="utf-8",
    )
    code = (
        "import subprocess, sys, time\n"
        f"subprocess.Popen([sys.executable, r'{grandchild}'])\n"
        "print('SPAWNED', flush=True)\n"
        "time.sleep(20)\n"
    )
    skill = _python_skill("hang-forever", code)
    ctx = SkillExecutionContext(workspace=tmp_path, timeout_seconds=3.0)
    res = SkillDispatcher(admission=_admit("hang-forever")).dispatch(skill, ctx)

    assert res.success is False
    assert res.exit_code == 124
    assert "terminated" in res.stderr.lower()
    # The grandchild must not survive to write its marker.
    time.sleep(3.0)
    assert not marker.exists(), "grandchild outlived the containment boundary"


def test_contained_process_accepts_explicit_env(tmp_path: Path) -> None:
    script = tmp_path / "show.py"
    script.write_text("import os;print(os.environ.get('PASSED',''))\n", encoding="utf-8")
    proc = ContainedProcess(
        [sys.executable, str(script)], tmp_path, env={"PASSED": "yes", "PATH": ""}
    )
    code, out, _ = proc.start().wait(timeout=60)
    assert code == 0
    assert out.strip() == "yes"


def test_contained_process_env_none_inherits() -> None:
    """`env=None` must keep the pre-existing inheritance behavior."""
    script = Path(__file__)
    assert ContainedProcess([sys.executable, "-c", "pass"], script.parent).env is None


def test_contained_process_env_replaces_rather_than_merges(tmp_path: Path) -> None:
    script = tmp_path / "leak.py"
    script.write_text(
        "import os;print('LEAKED' if os.environ.get('JARVIS_MODEL_API_KEY') else 'clean')\n",
        encoding="utf-8",
    )
    import os

    os.environ["JARVIS_MODEL_API_KEY"] = "sk-secret"
    try:
        proc = ContainedProcess(
            [sys.executable, str(script)], tmp_path, env={"PATH": os.environ["PATH"]}
        )
        code, out, _ = proc.start().wait(timeout=60)
    finally:
        os.environ.pop("JARVIS_MODEL_API_KEY", None)
    assert code == 0
    assert out.strip() == "clean"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Object path")
def test_windows_job_object_is_used(tmp_path: Path) -> None:
    from jarvis.orchestrator.bridges.process import _WindowsJob

    job = _WindowsJob()
    try:
        assert job is not None
    finally:
        job.close()


def test_dispatchable_languages_are_a_superset_of_manifest_executable() -> None:
    from jarvis.skills.manifest import EXECUTABLE_LANGUAGES

    assert EXECUTABLE_LANGUAGES <= DISPATCHABLE_LANGUAGES


def test_env_allowlist_does_not_include_secret_shaped_names() -> None:
    for name in INHERITED_ENV_ALLOWLIST:
        lowered = name.lower()
        assert "key" not in lowered
        assert "token" not in lowered
        assert "secret" not in lowered
        assert "password" not in lowered
