"""Tests for the antibug scanner.

Two jobs:

1. Prove each rule catches the real bug it was written for. Every rule in
   `bugscan.py` exists because it found something, so each gets a synthetic
   reproduction of that exact defect. A rule that catches nothing is worse than
   no rule, because it manufactures confidence.

2. Prove the scanner stays quiet on correct code. A scanner that cries wolf
   gets ignored, and an ignored scanner catches nothing. The regression tests
   below cover the false positives that actually appeared while building this:
   lambda parameters (18 of them) and `ClassDef.args`.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

from jarvis.qa.bugscan import (
    RULE_FABRICATED_SUCCESS as FABRICATED_SUCCESS,
)
from jarvis.qa.bugscan import (
    RULE_IMPORT_ERROR as IMPORT_ERROR,
)
from jarvis.qa.bugscan import (
    RULE_SWALLOWED_ERROR as SWALLOWED_ERROR,
)
from jarvis.qa.bugscan import (
    RULE_UNDEFINED_NAME as UNDEFINED_NAME,
)
from jarvis.qa.bugscan import (
    RULE_UNENFORCED_CLAIM as UNENFORCED_CLAIM,
)
from jarvis.qa.bugscan import (
    Finding,
    find_by_id,
    scan,
)
from jarvis.qa.triage import Triage, _apply_unified_diff, _split_patch, propose_apply


def _rules_for(
    source: str, tmp_path: Path, rule: str, deps: tuple[str, ...] = ("pydantic",)
) -> list[Finding]:
    """Run one rule over a synthetic file on disk."""
    pkg = tmp_path / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    target = pkg / "sample.py"
    target.write_text(textwrap.dedent(source), encoding="utf-8")
    specifiers = ",\n".join(f'    "{d}"' for d in deps)
    (tmp_path / "pyproject.toml").write_text(
        f"dependencies = [\n{specifiers}\n]\n", encoding="utf-8"
    )
    tree = ast.parse(target.read_text(encoding="utf-8"))

    from jarvis.qa import bugscan

    if rule == UNDEFINED_NAME:
        return bugscan.rule_undefined_name(target, tree, target.read_text(encoding="utf-8"), "pkg/sample.py")
    if rule == IMPORT_ERROR:
        return bugscan.rule_undeclared_import(target, tree, target.read_text(encoding="utf-8"), "pkg/sample.py")
    if rule == SWALLOWED_ERROR:
        return bugscan.rule_swallowed_error(target, tree, target.read_text(encoding="utf-8"), "pkg/sample.py")
    if rule == UNENFORCED_CLAIM:
        return bugscan.rule_unenforced_claim(target, tree, target.read_text(encoding="utf-8"), "pkg/sample.py")
    if rule == FABRICATED_SUCCESS:
        return bugscan.rule_fabricated_success(target, tree, target.read_text(encoding="utf-8"), "pkg/sample.py")
    raise AssertionError(rule)


# --- UNDEFINED_NAME ---------------------------------------------------------


def test_undefined_name_catches_the_model_name_bug(tmp_path: Path) -> None:
    """The real bug: a synthesis call referencing a name that never existed.

    It shipped because a bare `except Exception` turned the resulting NameError
    into a hardcoded "successfully" string, so the failure was invisible.
    """
    src = """
        def synthesize(client, messages, executed_tools):
            try:
                resp = client.chat.completions.create(model=model_name, messages=messages)
                return resp.text
            except Exception:
                return "Executed successfully"
    """
    findings = _rules_for(src, tmp_path, UNDEFINED_NAME)
    assert any("model_name" in f.message for f in findings)


def test_undefined_name_catches_numpy_without_dependency(tmp_path: Path) -> None:
    """The real bug: numpy used but never installed or declared."""
    src = """
        def rms(data):
            return float(np.sqrt(np.mean(data)))
    """
    findings = _rules_for(src, tmp_path, UNDEFINED_NAME)
    assert any("np" in f.message for f in findings)


def test_undefined_name_catches_missing_typing_import(tmp_path: Path) -> None:
    """The real bug: `Any` used in an annotation, never imported."""
    src = """
        from __future__ import annotations

        def cache() -> dict[str, Any]:
            return {}
    """
    findings = _rules_for(src, tmp_path, UNDEFINED_NAME)
    assert any("Any" in f.message for f in findings)


def test_undefined_name_catches_missing_local_function(tmp_path: Path) -> None:
    """The real bug: `get_default_registry` used in `_cmd_skill_admit`."""
    src = """
        def admit(skill_id):
            reg = get_default_registry()
            return reg
    """
    findings = _rules_for(src, tmp_path, UNDEFINED_NAME)
    assert any("get_default_registry" in f.message for f in findings)


@pytest.mark.parametrize(
    "src",
    [
        # lambda parameters produced 18 false positives before this was fixed
        "xs = [1]\nxs.sort(key=lambda m: m.score)\n",
        "f = lambda a, b=1, *c, **d: a\n",
        # walrus, comprehension targets, with/for bindings
        "def f(rows):\n    return [y for y in rows]\n",
        "def f(it):\n    for item in it:\n        pass\n    return item\n",
        "def f(d):\n    if (n := len(d)):\n        return n\n    return 0\n",
        "def f(cm):\n    with cm as handle:\n        return handle\n",
        # imports under aliases, star-free
        "import os.path as p\nfrom typing import Any as A\ndef f() -> A:\n    return None\n",
        # exception binding and global decls
        "def f():\n    try:\n        pass\n    except ValueError as err:\n        return err\n",
    ],
)
def test_undefined_name_is_quiet_on_valid_code(src: str, tmp_path: Path) -> None:
    findings = _rules_for(src, tmp_path, UNDEFINED_NAME)
    assert findings == [], f"false positives: {[f.message for f in findings]}"


def test_classdef_does_not_crash_the_name_rule(tmp_path: Path) -> None:
    """`ClassDef` has no `.args`; grouping it with functions broke the rule
    across all 120 files until the scanner reported its own error."""
    src = """
        class Thing:
            attr = 1

            def method(self, value):
                return value
    """
    assert _rules_for(src, tmp_path, UNDEFINED_NAME) == []


# --- IMPORT_ERROR -----------------------------------------------------------


def test_import_error_catches_the_dead_ai_subsystem(tmp_path: Path) -> None:
    """The real bug that silently killed every LLM call.

    A provider SDK imported inside `_resolve` and declared nowhere, with each
    branch ending in `except: pass`, so the engine degraded to "offline" with no
    diagnostic.

    Uses a module name that cannot be installed in any environment, so the test
    keeps testing the rule's mechanics after the real project fixes the real
    `openai` import. The historical case is pinned separately by
    `test_declared_and_installed_dependency_is_no_longer_reported`.
    """
    src = """
        def _resolve(self):
            try:
                from provider_sdk_that_does_not_exist import Client
                self._client = Client(api_key="x")
                return
            except Exception:
                pass
            self._resolved_provider = "offline"
    """
    findings = _rules_for(src, tmp_path, IMPORT_ERROR)
    assert findings, "should flag an undeclared runtime import"
    assert "provider_sdk_that_does_not_exist" in findings[0].message
    assert findings[0].severity == "critical", (
        "a broad handler that swallows the failure is the silent-death pattern "
        "and must be critical, not a packaging nit"
    )


def test_installed_but_undeclared_is_reported_as_low(tmp_path: Path) -> None:
    """Works locally, breaks on a clean install: still a real defect.

    This is the trap that let the project ship an undeclared provider SDK: it
    was importable on the author's machine, so nothing looked wrong locally.
    """
    src = """
        def f():
            import pytest
            return pytest
    """
    findings = _rules_for(src, tmp_path, IMPORT_ERROR)
    assert findings, "installed-but-undeclared import must still be reported"
    assert findings[0].severity == "low", (
        "being installed locally downgrades severity; it does not make the "
        "undeclared dependency disappear"
    )


def test_import_error_ignores_declared_and_stdlib_and_relative(tmp_path: Path) -> None:
    src = """
        import json
        from pathlib import Path
        from jarvis.kernel.event_log import EventLog
        from .sibling import thing
        from pydantic import BaseModel

        def f():
            from cryptography.hazmat.primitives import hashes
            return json, Path, EventLog, thing, BaseModel, hashes
    """
    assert (
        _rules_for(
            src, tmp_path, IMPORT_ERROR, deps=("pydantic", "cryptography")
        )
        == []
    )


def test_import_error_ignores_top_level_imports(tmp_path: Path) -> None:
    """A top-level import of a missing package fails loudly at import time;
    only nested imports are the silent trap."""
    src = """
        import openai

        def f():
            return openai
    """
    assert _rules_for(src, tmp_path, IMPORT_ERROR) == []


# --- SWALLOWED_ERROR --------------------------------------------------------


def test_swallowed_error_flags_bare_except(tmp_path: Path) -> None:
    src = """
        def f():
            try:
                run()
            except:
                pass
    """
    findings = _rules_for(src, tmp_path, SWALLOWED_ERROR)
    assert findings
    assert findings[0].severity == "high"


def test_swallowed_error_flags_named_exception_discarded(tmp_path: Path) -> None:
    src = """
        def f():
            try:
                run()
            except ValueError as err:
                pass
    """
    findings = _rules_for(src, tmp_path, SWALLOWED_ERROR)
    assert findings
    assert findings[0].severity == "high"
    assert "err" in findings[0].message


def test_swallowed_error_typed_handler_is_low(tmp_path: Path) -> None:
    """`except OSError: pass` is usually deliberate best-effort cleanup."""
    src = """
        def f():
            try:
                run()
            except OSError:
                pass
    """
    findings = _rules_for(src, tmp_path, SWALLOWED_ERROR)
    assert findings
    assert findings[0].severity == "low"


def test_swallowed_error_ignores_logging_and_reraise(tmp_path: Path) -> None:
    src = """
        import logging

        logger = logging.getLogger(__name__)

        def f():
            try:
                run()
            except OSError:
                logger.warning("failed", exc_info=True)

        def g():
            try:
                run()
            except OSError:
                raise
    """
    assert _rules_for(src, tmp_path, SWALLOWED_ERROR) == []


# --- FABRICATED_SUCCESS -----------------------------------------------------


def test_fabricated_success_catches_the_hardcoded_success_string(tmp_path: Path) -> None:
    """The real bug: a handler that asserts success it never observed."""
    src = """
        def synthesize(n):
            try:
                return call()
            except Exception:
                final_text = f"Executed {n} system actions successfully, sir."
    """
    findings = _rules_for(src, tmp_path, FABRICATED_SUCCESS)
    assert findings
    assert findings[0].severity == "high"


def test_fabricated_success_allows_a_message_that_reports_the_error(tmp_path: Path) -> None:
    src = """
        def f():
            try:
                return call()
            except Exception:
                msg = f"failed: {exc}"
    """
    assert _rules_for(src, tmp_path, FABRICATED_SUCCESS) == []


# --- UNENFORCED_CLAIM -------------------------------------------------------


def test_unenforced_claim_flags_pinned_sha_claim(tmp_path: Path) -> None:
    src = """
        def admit():
            print(f"  pinned sha256: {digest}")
    """
    findings = _rules_for(src, tmp_path, UNENFORCED_CLAIM)
    assert findings
    assert findings[0].severity == "low"


def test_unenforced_claim_ignores_comments_and_docstrings(tmp_path: Path) -> None:
    src = '''
        # historically we advertised a strict path jail
        """Never aborts on entry."""
        def f():
            return 1
    '''
    assert _rules_for(src, tmp_path, UNENFORCED_CLAIM) == []


# --- scanner plumbing -------------------------------------------------------


#: Undeclared-and-uninstalled third-party imports currently present in the
#: tree. Recorded deliberately rather than asserted empty: these are real
#: packaging defects, and the honest state is "known, not yet fixed".
#:
#: This baseline must shrink, never grow. Fixing a dependency means removing
#: its line here; introducing a new one breaks the test. That is the point.
#:
#: History: the four `openai` entries (jarvis_voice.py:374/399/415/456) were
#: removed after `openai` was declared and installed, which is what actually
#: brought the AI subsystem back online. `groq` remains: it is an alternative
#: provider, not a requirement.
_KNOWN_CRITICAL_IMPORTS = frozenset(
    {
        "src/jarvis/live_boot.py:105 faster_whisper",
        "src/jarvis/live_boot.py:201 faster_whisper",
        "src/jarvis/multimodal/audio_io.py:232 pyaudio",
        "src/jarvis/multimodal/audio_io.py:340 pyaudio",
        "src/jarvis/multimodal/jarvis_voice.py:387 groq",
        "src/jarvis/multimodal/jarvis_voice.py:632 speech_recognition",
        "src/jarvis/multimodal/neural_tts.py:106 edge_tts",
        "src/jarvis/multimodal/neural_tts.py:145 pydub",
        "src/jarvis/multimodal/neural_tts.py:155 numpy",
        "src/jarvis/multimodal/neural_tts.py:157 soundfile",
        "src/jarvis/multimodal/neural_tts.py:176 pyttsx3",
        "src/jarvis/ui/voice_listener.py:75 win32com.client",
        "src/jarvis/ui/voice_listener.py:128 pyttsx3",
    }
)


def _imported_module(finding) -> str:
    """Extract the module name from an IMPORT_ERROR message."""
    return finding.message.split("imports ")[1].split(" ")[0].strip("'\"")


def test_import_error_rule_is_actually_live_on_the_real_tree() -> None:
    """Guards against the rule silently degrading to a no-op.

    The rule once searched for pyproject.toml beside each source file instead of
    at the repo root, saw an empty declared set, and returned early on every
    file. It also misclassified function-local imports as top-level, so it could
    never match the lazy-import pattern it was written for. Both bugs made it
    report zero findings while looking healthy.
    """
    report = scan("src/jarvis", rules=["IMPORT_ERROR"])
    assert report.findings, "IMPORT_ERROR produced no findings at all"
    undeclared = {_imported_module(f) for f in report.findings}
    # Still undeclared, so the rule has real work left to do on real files.
    assert undeclared & {"pyaudio", "faster_whisper", "soundfile"}, (
        f"expected known-undeclared voice modules, got {sorted(undeclared)}"
    )


def test_declared_and_installed_dependency_is_no_longer_reported() -> None:
    """The bug this scanner was built to find must stay fixed.

    `openai` was imported inside `LLMEngine._resolve` and swallowed by a broad
    handler, so the whole AI subsystem degraded to offline with no diagnostic
    while appearing healthy. It is now a declared dependency, so it must no
    longer be reported.
    """
    report = scan("src/jarvis", rules=["IMPORT_ERROR"])
    reported = {_imported_module(f) for f in report.findings}
    assert "openai" not in reported, (
        "openai is declared and installed; it must not be reported as undeclared"
    )


def test_critical_imports_match_the_recorded_baseline() -> None:
    """Fails on any NEW critical defect, and reminds us to shrink the set."""
    report = scan("src/jarvis")
    critical = [f for f in report.findings if f.severity == "critical"]
    found = {
        f"{f.file}:{f.line} {_imported_module(f) if 'imports' in f.message else f.rule}"
        for f in critical
    }
    new = found - _KNOWN_CRITICAL_IMPORTS
    assert not new, (
        "new critical defects introduced: "
        + "; ".join(sorted(new))
        + ". Fix them, or record why they are acceptable."
    )
    fixed = _KNOWN_CRITICAL_IMPORTS - found
    assert not fixed, (
        "these previously known criticals are now resolved - remove them from "
        "_KNOWN_CRITICAL_IMPORTS: " + "; ".join(sorted(fixed))
    )


def test_optional_imports_are_not_reported_as_critical() -> None:
    """A guarded optional import is a packaging gap, not a critical defect.

    Severity must reflect whether the failure can actually be seen. Reporting
    every undeclared import as critical would be noise, and would train the
    reader to ignore the rule.
    """
    report = scan("src/jarvis", rules=["IMPORT_ERROR"])
    for f in report.findings:
        if "install_startup" in f.message or "opentelemetry" in f.message:
            assert f.severity != "critical", (
                f"{f.file}:{f.line} is a project-local or already-declared "
                f"module and should not be critical: {f.message}"
            )
    critical_modules = {
        f.message.split("imports ")[1].split(" ")[0].split(".")[0]
        for f in report.findings
        if f.severity == "critical"
    }
    assert "install_startup" not in critical_modules
    assert "opentelemetry" not in critical_modules


def test_scan_reports_its_own_errors_rather_than_crashing() -> None:
    report = scan("src/jarvis")
    assert report.scanner_errors == []


def test_scan_json_is_serializable() -> None:
    import json

    payload = json.loads(scan("src/jarvis", rules=["UNDEFINED_NAME"]).to_json())
    assert "findings" in payload
    assert "by_severity" in payload


def test_finding_ids_are_stable_and_unique() -> None:
    a = scan("src/jarvis")
    b = scan("src/jarvis")
    assert [f.finding_id for f in a.findings] == [f.finding_id for f in b.findings]
    ids = [f.finding_id for f in a.findings]
    assert len(ids) == len(set(ids))


def test_find_by_id_resolves() -> None:
    report = scan("src/jarvis")
    if not report.findings:
        pytest.skip("no findings to resolve")
    first = report.findings[0]
    assert find_by_id(report, first.finding_id) is first
    assert find_by_id(report, "nope-000000") is None


# --- triage gating ----------------------------------------------------------


def test_triage_reports_unavailable_instead_of_inventing_a_fix() -> None:
    """With no provider, triage must say so and propose nothing.

    This is the whole point: the AI layer is additive. An LLM that is silently
    broken must not be able to fabricate patches or, worse, look authoritative.
    """
    from jarvis.qa.triage import triage_one

    finding = Finding(
        rule=UNDEFINED_NAME, severity="critical",
        file="pkg/x.py", line=1, message="m", finding_id="f1",
    )
    result = triage_one(finding, llm=_DeadLLM())
    assert result.patch == ""
    assert "no LLM provider" in result.ai_status
    assert "Install a provider SDK" in result.ai_status


class _DeadLLM:
    """Stands in for the real engine, which resolves offline here."""

    _client = None
    _resolved_provider = "offline"
    _resolved_model = "none"
    resolve_errors = ["openai: ModuleNotFoundError: No module named 'openai'"]

    def _resolve(self) -> None:
        return None


def test_split_patch_separates_diff_from_prose() -> None:
    patch, prose = _split_patch(
        "This happens because the name is never bound.\n"
        "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-old\n+new\n"
    )
    assert patch.startswith("--- a/x.py")
    assert "never bound" in prose


def test_apply_unified_diff_roundtrip() -> None:
    original = "one\ntwo\nthree\n"
    patch = "--- a/f\n+++ b/f\n@@ -2 +2 @@\n-two\n+TWO\n"
    assert _apply_unified_diff(original, patch) == "one\nTWO\nthree\n"


def test_apply_unified_diff_rejects_stale_context() -> None:
    """A patch whose context no longer matches must fail, not half-apply."""
    original = "totally\ndifferent\ncontent\n"
    patch = "--- a/f\n+++ b/f\n@@ -2 +2 @@\n-two\n+TWO\n"
    assert _apply_unified_diff(original, patch) is None


def test_propose_apply_is_a_dry_run_by_default(tmp_path: Path) -> None:
    finding = Finding(
        rule=UNDEFINED_NAME, severity="critical",
        file="src/jarvis/does_not_exist.py", line=1, message="m", finding_id="f1",
    )
    result = propose_apply(finding, Triage(finding=finding, patch=""), dry_run=True)
    assert result.ok is False
    assert "no patch" in result.message


def test_propose_apply_refuses_a_patch_that_would_not_compile(tmp_path: Path) -> None:
    """A syntax error from a bad patch is worse than no patch at all."""
    target = Path(__file__).resolve().parents[2] / "src" / "jarvis" / "skills" / "admission.py"
    original = target.read_text(encoding="utf-8")
    broken = original.replace("import json", "import json\ndef (((", 1)

    from jarvis.qa.triage import _apply_unified_diff  # noqa: F401
    import difflib

    diff = "\n".join(
        difflib.unified_diff(
            original.splitlines(), broken.splitlines(),
            fromfile="a/x", tofile="b/x", lineterm="",
        )
    )
    finding = Finding(
        rule=UNDEFINED_NAME, severity="critical",
        file="src/jarvis/skills/admission.py", line=1, message="m", finding_id="f1",
    )
    result = propose_apply(finding, Triage(finding=finding, patch=diff), dry_run=False)
    assert result.ok is False
    assert "would not compile" in result.message
    # and the file must be untouched
    assert target.read_text(encoding="utf-8") == original
