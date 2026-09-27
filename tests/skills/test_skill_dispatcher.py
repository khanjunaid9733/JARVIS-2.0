from __future__ import annotations

from pathlib import Path
import pytest

from jarvis.kernel.event_log import EventLog
from jarvis.skills.admission import SkillAdmissionPolicy
from jarvis.skills.context import SkillExecutionContext
from jarvis.skills.dispatcher import SkillDispatcher
from jarvis.skills.health import SkillHealthChecker
from jarvis.skills.manifest import parse_skill_markdown


def _admit(*skill_ids: str) -> SkillAdmissionPolicy:
    """Admission policy that permits the fixture skills under test.

    ADR-011 S4 makes execution default-deny, so tests that assert on dispatch
    mechanics must say which skills they admit. Refusal behavior itself is
    covered in tests/skills/test_admission_policy.py.
    """
    return SkillAdmissionPolicy(entries=frozenset(skill_ids))


def test_dispatcher_dry_run(tmp_path):
    doc = """---
name: media-mock
description: Mock media skill.
---
# Mock Media
## Core Workflows
```python
print("Mock converting {input_file} to {output_file}")
```
"""
    skill = parse_skill_markdown(doc)
    ctx = SkillExecutionContext(
        workspace=tmp_path,
        parameters={"input_file": "sample.wav", "output_file": "sample.mp3"},
        dry_run=True,
    )
    dispatcher = SkillDispatcher(admission=_admit("media-mock"))
    res = dispatcher.dispatch(skill, ctx)

    assert res.success is True
    assert res.exit_code == 0
    assert "[DRY-RUN]" in res.stdout
    assert "sample.wav" in res.stdout


def test_dispatcher_executes_python_step(tmp_path):
    doc = """---
name: python-calculator
description: Simple Python calculator.
---
# Calculator
## Core Workflows
```python
result = 40 + 2
print(f"CALCULATED_ANSWER={result}")
```
"""
    skill = parse_skill_markdown(doc)
    # Ensure no blocking prerequisites
    skill.prerequisites.required_binaries.clear()
    skill.prerequisites.required_env_vars.clear()
    skill.prerequisites.required_python_modules.clear()

    ctx = SkillExecutionContext(workspace=tmp_path)
    dispatcher = SkillDispatcher(admission=_admit("python-calculator"))
    res = dispatcher.dispatch(skill, ctx)

    assert res.success is True
    assert res.exit_code == 0
    assert "CALCULATED_ANSWER=42" in res.stdout


def test_dispatcher_refuses_when_prerequisites_missing(tmp_path):
    doc = """---
name: missing-tool
description: Tool with missing prereq.
---
# Tool
## Core Workflows
```python
print("hello")
```
"""
    skill = parse_skill_markdown(doc)
    skill.prerequisites.required_binaries = ["uninstalled_phantom_binary_abc"]

    ctx = SkillExecutionContext(workspace=tmp_path, dry_run=False)
    dispatcher = SkillDispatcher(admission=_admit("missing-tool"))
    res = dispatcher.dispatch(skill, ctx)

    assert res.success is False
    assert res.is_refused is True
    assert "missing binaries" in (res.refusal_reason or "")


def test_dispatcher_handles_step_failure(tmp_path):
    doc = """---
name: faulty-script
description: Script that exits with error.
---
# Faulty Script
## Core Workflows
```python
import sys
print("Starting up...", file=sys.stderr)
sys.exit(5)
```
"""
    skill = parse_skill_markdown(doc)
    skill.prerequisites.required_binaries.clear()
    skill.prerequisites.required_env_vars.clear()
    skill.prerequisites.required_python_modules.clear()

    ctx = SkillExecutionContext(workspace=tmp_path)
    dispatcher = SkillDispatcher(admission=_admit("faulty-script"))
    res = dispatcher.dispatch(skill, ctx)

    assert res.success is False
    assert res.exit_code == 5
    assert "Step 1 failed with exit code 5" in (res.error or "")
    assert "Starting up..." in res.stderr


def _bash_skill(code: str):
    skill = parse_skill_markdown(
        f"""---
name: bash-mock
description: Mock bash skill.
---
# Bash Mock
## Core Workflows
```bash
{code}
```
"""
    )
    skill.prerequisites.required_binaries.clear()
    skill.prerequisites.required_env_vars.clear()
    skill.prerequisites.required_python_modules.clear()
    return skill


def test_failing_shell_step_is_not_reported_as_success(tmp_path):
    """Regression: on Windows a ``bash`` step ran through PowerShell, whose
    ``-File`` mode returns 0 even when the script fails - so broken skills were
    reported as successful."""
    dispatcher = SkillDispatcher(admission=_admit("bash-mock"))
    res = dispatcher.dispatch(
        _bash_skill("exit 7"), SkillExecutionContext(workspace=tmp_path)
    )
    assert res.success is False
    assert res.exit_code == 7


def test_succeeding_shell_step_is_reported_as_success(tmp_path):
    dispatcher = SkillDispatcher(admission=_admit("bash-mock"))
    res = dispatcher.dispatch(
        _bash_skill("echo shell-ok"), SkillExecutionContext(workspace=tmp_path)
    )
    assert res.success is True
    assert res.exit_code == 0
    assert "shell-ok" in res.stdout


def test_powershell_fallback_wrapper_propagates_exit_code():
    from jarvis.skills.dispatcher import _wrap_powershell_exit_code

    wrapped = _wrap_powershell_exit_code("some-native-command")
    assert "$LASTEXITCODE" in wrapped
    assert wrapped.startswith("some-native-command")


def _audit_skill():
    return parse_skill_markdown(
        """---
name: audit-mock
description: Mock skill with no prerequisites.
---
# Audit Mock
## Core Workflows
```python
print("audited")
```
"""
    )


def test_dispatcher_audits_to_a_real_event_log(tmp_path):
    """Regression: the dispatcher called ``EventLog.append(event_type=...,
    payload=...)`` but ``append`` takes a single ``Event``. The resulting
    ``TypeError`` was swallowed, so no skill audit ever reached the log."""
    log = EventLog(db_path=tmp_path / "log.db")
    skill = _audit_skill()
    ctx = SkillExecutionContext(workspace=tmp_path)

    res = SkillDispatcher(event_sink=log, admission=_admit("audit-mock")).dispatch(
        skill, ctx
    )
    assert res.success is True

    types = [e.event_type for e in log.replay() if e.stream_id == "skills"]
    assert "skill.dispatched" in types
    assert "skill.succeeded" in types
    # replay() itself verifies every hash in the chain.


def test_dispatcher_audits_refusal_and_failure(tmp_path):
    log = EventLog(db_path=tmp_path / "log.db")
    dispatcher = SkillDispatcher(
        event_sink=log, admission=_admit("audit-mock", "failing-mock")
    )

    refused = _audit_skill()
    refused.prerequisites.required_binaries = ["uninstalled_phantom_binary_abc"]
    res = dispatcher.dispatch(refused, SkillExecutionContext(workspace=tmp_path))
    assert res.is_refused is True

    failing = parse_skill_markdown(
        """---
name: failing-mock
description: Exits non-zero.
---
# Failing Mock
## Core Workflows
```python
import sys
sys.exit(3)
```
"""
    )
    failing.prerequisites.required_binaries.clear()
    failing.prerequisites.required_python_modules.clear()
    res2 = dispatcher.dispatch(failing, SkillExecutionContext(workspace=tmp_path))
    assert res2.success is False

    types = [e.event_type for e in log.replay() if e.stream_id == "skills"]
    assert "skill.refused" in types
    assert "skill.failed" in types


def test_dispatcher_records_audit_sink_failures_instead_of_hiding_them(tmp_path):
    from jarvis.skills.telemetry import get_skill_metrics

    class _BrokenSink:
        def append(self, event):
            raise RuntimeError("sink down")

    before = get_skill_metrics().audit_emit_failures
    skill = _audit_skill()
    # Execution must still succeed even when the audit sink is broken ...
    res = SkillDispatcher(
        event_sink=_BrokenSink(), admission=_admit("audit-mock")
    ).dispatch(skill, SkillExecutionContext(workspace=tmp_path))
    assert res.success is True
    # ... but the dropped audit must be counted, never silently ignored.
    assert get_skill_metrics().audit_emit_failures > before
    # And observable directly on the execution result across process boundaries
    assert len(res.audit_errors) > 0
    assert any("sink down" in err for err in res.audit_errors)


def test_dispatcher_auto_wraps_and_prints_single_expression(tmp_path):
    doc = """---
name: expr-mock
description: Expression evaluation.
---
# Expr Mock
## Core Workflows
```python
100 + 42
```
"""
    skill = parse_skill_markdown(doc)
    skill.prerequisites.required_binaries.clear()
    skill.prerequisites.required_python_modules.clear()

    ctx = SkillExecutionContext(workspace=tmp_path)
    res = SkillDispatcher(admission=_admit("expr-mock")).dispatch(skill, ctx)
    assert res.success is True
    assert "142" in res.stdout


def test_dispatcher_auto_imports_and_evaluates_semicolon_expression(tmp_path):
    doc = """---
name: semicolon-mock
description: Semicolon expression evaluation.
---
# Semicolon Mock
## Core Workflows
```python
import math; math.sqrt(16)
```
"""
    skill = parse_skill_markdown(doc)
    skill.prerequisites.required_binaries.clear()
    skill.prerequisites.required_python_modules.clear()

    ctx = SkillExecutionContext(workspace=tmp_path)
    res = SkillDispatcher(admission=_admit("semicolon-mock")).dispatch(skill, ctx)
    assert res.success is True
    assert "4.0" in res.stdout


def test_dispatcher_auto_imports_common_modules(tmp_path):
    doc = """---
name: auto-import-mock
description: Auto import module test.
---
# Auto Import Mock
## Core Workflows
```python
os.path.basename("/path/to/target.txt")
```
"""
    skill = parse_skill_markdown(doc)
    skill.prerequisites.required_binaries.clear()
    skill.prerequisites.required_python_modules.clear()

    ctx = SkillExecutionContext(workspace=tmp_path)
    res = SkillDispatcher(admission=_admit("auto-import-mock")).dispatch(skill, ctx)
    assert res.success is True
    assert "target.txt" in res.stdout


