"""ADR-011 S1 regression tests: parse-time admission.

An untagged code fence in a skill document is documentation prose, not
something to run. Before S1, `_extract_code_blocks` defaulted an untagged
fence to `bash`, which meant a prose skill like `3d-games` was dispatched by
running its own Markdown description through a shell (exit 127).

Admission is now decided by the fence's explicit language tag:
- untagged  -> `text`, inert
- `text`/unknown -> inert
- `bash`/`sh`/`powershell`/`python`/`http` -> admitted
"""

from __future__ import annotations

from pathlib import Path

from jarvis.skills.dispatcher import DISPATCHABLE_LANGUAGES
from jarvis.skills.manifest import (
    EXECUTABLE_LANGUAGES,
    UNTAGGED_FENCE_LANGUAGE,
    SkillWorkflowStep,
    parse_skill_markdown,
)

FENCE = "`" * 3


def _doc(workflow: str) -> str:
    return (
        "---\n"
        "name: sample\n"
        "description: sample skill\n"
        "---\n"
        "\n"
        "# Sample\n"
        "\n"
        "## Purpose\n"
        "Demonstrates fence admission.\n"
        "\n"
        "## Workflow\n"
        f"{workflow}\n"
    )


def _steps(workflow: str) -> list[SkillWorkflowStep]:
    return parse_skill_markdown(_doc(workflow), "sample").workflow_steps


def test_untagged_fence_is_text_not_bash() -> None:
    steps = _steps(f"{FENCE}\n1. **Open a 3D game engine**\n2. **Load a scene**\n{FENCE}")
    assert len(steps) == 1
    assert steps[0].language == UNTAGGED_FENCE_LANGUAGE == "text"
    assert steps[0].is_executable is False


def test_untagged_fence_makes_skill_not_runnable() -> None:
    manifest = parse_skill_markdown(
        _doc(f"{FENCE}\n1. **Do a thing**\n2. **Do another**\n{FENCE}"), "sample"
    )
    assert manifest.is_runnable is False


def test_prose_skill_is_not_runnable_and_dispatchable_step_count_is_zero() -> None:
    """The `3d-games` shape: a numbered list, not a program."""
    manifest = parse_skill_markdown(
        _doc(f"{FENCE}\n1. **Open a 3D game engine**\n2. **Load a scene**\n{FENCE}"),
        "3d-games",
    )
    dispatchable = [
        s for s in manifest.workflow_steps if s.language in DISPATCHABLE_LANGUAGES
    ]
    assert dispatchable == []


def test_explicit_bash_fence_still_runs() -> None:
    steps = _steps(f"{FENCE}bash\necho hi\n{FENCE}")
    assert steps[0].language == "bash"
    assert steps[0].is_executable is True


def test_explicit_sh_fence_is_dispatchable() -> None:
    """`sh` stays admitted for skills that already tag it."""
    steps = _steps(f"{FENCE}sh\necho hi\n{FENCE}")
    assert steps[0].language == "sh"
    assert steps[0].language in DISPATCHABLE_LANGUAGES


def test_explicit_powershell_and_python_remain_executable() -> None:
    for lang in ("powershell", "python"):
        steps = _steps(f"{FENCE}{lang}\nvalue = 1\n{FENCE}")
        assert steps[0].language == lang
        assert steps[0].is_executable is True


def test_unknown_language_is_inert_but_preserved() -> None:
    """An unrecognized tag must be kept for inspection and never executed."""
    steps = _steps(f"{FENCE}rust\nfn main() {{}}\n{FENCE}")
    assert len(steps) == 1
    assert steps[0].language == "rust"
    assert steps[0].code.strip()
    assert steps[0].is_executable is False
    assert "rust" not in EXECUTABLE_LANGUAGES


def test_explicit_text_fence_is_inert() -> None:
    steps = _steps(f"{FENCE}text\nsome documentation\n{FENCE}")
    assert steps[0].language == "text"
    assert steps[0].is_executable is False


def test_mixed_fences_admit_only_tagged_ones() -> None:
    steps = _steps(
        f"{FENCE}bash\necho ok\n{FENCE}\n\n{FENCE}\nprose example\n{FENCE}\n\n"
        f"{FENCE}python\nx = 1\n{FENCE}"
    )
    assert [s.is_executable for s in steps] == [True, False, True]


def test_empty_executable_fence_yields_no_step() -> None:
    """A bare fence has no body; the extractor's regex requires one, so it is
    dropped entirely. Either way there is nothing to execute."""
    steps = _steps(f"{FENCE}bash\n{FENCE}")
    assert [s.is_executable for s in steps] == []


def test_is_executable_requires_both_language_and_code() -> None:
    assert SkillWorkflowStep(step_index=1, language="bash", code="x").is_executable
    assert not SkillWorkflowStep(step_index=1, language="bash", code="   ").is_executable
    assert not SkillWorkflowStep(step_index=1, language="text", code="x").is_executable


def test_step_default_language_is_text() -> None:
    """The dataclass default must not silently imply a shell."""
    assert SkillWorkflowStep(step_index=1).language == "text"


def test_real_prose_skill_from_library_is_not_runnable() -> None:
    """Guard against the actual library entry, if it is present."""
    path = Path(".agents/skills/3d-games/SKILL.md")
    if not path.exists():
        return
    manifest = parse_skill_markdown(
        path.read_text(encoding="utf-8"), "3d-games"
    )
    assert manifest.is_runnable is False
