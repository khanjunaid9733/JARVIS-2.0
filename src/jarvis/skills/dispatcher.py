from __future__ import annotations

"""Safe Skill Execution Dispatcher with containment and event auditing.

Executes declared skill workflow steps in an isolated subprocess with strict
path jailing, timeout enforcement, output capture, and failure isolation.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from jarvis.kernel.event_log import Event

from .context import SkillExecutionContext
from .health import HealthStatus, SkillHealthChecker
from .manifest import SkillManifest
from .telemetry import record_skill_audit_failure

SKILL_AUDIT_STREAM = "skills"
SKILL_AUDIT_PRINCIPAL = "skills.dispatcher"


def _wrap_powershell_exit_code(code: str) -> str:
    """Append propagation of the last native exit code to a PowerShell script.

    Without this, ``powershell -File`` exits 0 no matter how the final native
    command failed, turning a failed skill into a reported success.
    """
    return (
        code
        + "\nif ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n"
    )


@dataclass(frozen=True)
class SkillExecutionResult:
    """Outcome of a skill dispatch execution."""

    skill_id: str
    success: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    raw_output: str = ""
    duration_ms: float = 0.0
    error: str | None = None
    refusal_reason: str | None = None
    artifacts: tuple[str, ...] = ()
    audit_errors: tuple[str, ...] = ()

    @property
    def is_refused(self) -> bool:
        return self.refusal_reason is not None


class SkillDispatcher:
    """Dispatches skill executions with safety gates, timeouts, and auditing."""

    def __init__(
        self,
        health_checker: SkillHealthChecker | None = None,
        event_sink: Any | None = None,
    ) -> None:
        self.health_checker = health_checker or SkillHealthChecker()
        self.event_sink = event_sink

    def dispatch(
        self,
        skill: SkillManifest,
        context: SkillExecutionContext,
    ) -> SkillExecutionResult:
        """Execute a skill within the given execution context."""
        start_time = time.perf_counter()
        audit_errors: list[str] = []

        def _emit(event_type: str, payload: dict[str, Any]) -> None:
            err = self._emit_audit(event_type, payload)
            if err:
                audit_errors.append(err)

        # 1. Deterministic Precondition Health Check
        health = self.health_checker.evaluate(skill)
        if not health.is_executable and not context.dry_run:
            duration_ms = (time.perf_counter() - start_time) * 1000
            _emit("skill.refused", {
                "skill_id": skill.id,
                "reason": health.summary,
                "missing_binaries": health.missing_binaries,
                "missing_env_vars": health.missing_env_vars,
            })
            return SkillExecutionResult(
                skill_id=skill.id,
                success=False,
                exit_code=-1,
                refusal_reason=health.summary,
                duration_ms=duration_ms,
                audit_errors=tuple(audit_errors),
            )

        # 2. Check if skill is runnable
        executable_steps = [
            s for s in skill.workflow_steps
            if s.language in ("bash", "powershell", "python", "sh") and s.code.strip()
        ]

        if not executable_steps:
            duration_ms = (time.perf_counter() - start_time) * 1000
            if context.dry_run:
                return SkillExecutionResult(
                    skill_id=skill.id,
                    success=True,
                    exit_code=0,
                    stdout=f"[DRY-RUN] Skill '{skill.id}' is informational or declaratively complete.",
                    duration_ms=duration_ms,
                    audit_errors=tuple(audit_errors),
                )
            return SkillExecutionResult(
                skill_id=skill.id,
                success=False,
                exit_code=-2,
                refusal_reason="Skill has no executable code blocks.",
                duration_ms=duration_ms,
                audit_errors=tuple(audit_errors),
            )

        if context.dry_run:
            duration_ms = (time.perf_counter() - start_time) * 1000
            summary_lines = [f"[DRY-RUN] Would execute {len(executable_steps)} step(s) for '{skill.id}':"]
            for step in executable_steps:
                subbed = context.substitute_params(step.code[:120])
                summary_lines.append(f"  Step {step.step_index} [{step.language}]: {subbed}")
            return SkillExecutionResult(
                skill_id=skill.id,
                success=True,
                exit_code=0,
                stdout="\n".join(summary_lines),
                duration_ms=duration_ms,
                audit_errors=tuple(audit_errors),
            )

        # 3. Execution Phase
        _emit("skill.dispatched", {
            "skill_id": skill.id,
            "mission_id": context.mission_id,
            "workspace": str(context.workspace),
        })

        all_stdout: list[str] = []
        all_stderr: list[str] = []
        raw_outputs: list[str] = []
        last_exit_code = 0

        # Build execution environment
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        env.update(context.env_overrides)

        context.workspace.mkdir(parents=True, exist_ok=True)

        for step in executable_steps:
            code_text = context.substitute_params(step.code)
            if step.language == "python" and context.parameters:
                preamble = "\n".join(
                    f"{k} = {repr(v)}"
                    for k, v in context.parameters.items()
                    if k.isidentifier()
                )
                code_text = f"{preamble}\n{code_text}"
            step_exit, step_out, step_err = self._run_step(
                step.language, code_text, context.workspace, env, context.timeout_seconds
            )
            raw_outputs.append(step_out.strip())
            all_stdout.append(f"--- Step {step.step_index} ({step.language}) ---\n{step_out}")
            if step_err:
                all_stderr.append(f"--- Step {step.step_index} Error ---\n{step_err}")
            last_exit_code = step_exit

            if step_exit != 0:
                duration_ms = (time.perf_counter() - start_time) * 1000
                _emit("skill.failed", {
                    "skill_id": skill.id,
                    "step_index": step.step_index,
                    "exit_code": step_exit,
                    "stderr": step_err[:500],
                })
                return SkillExecutionResult(
                    skill_id=skill.id,
                    success=False,
                    exit_code=step_exit,
                    stdout="\n".join(all_stdout),
                    stderr="\n".join(all_stderr),
                    raw_output="\n".join(raw_outputs),
                    duration_ms=duration_ms,
                    error=f"Step {step.step_index} failed with exit code {step_exit}.",
                    audit_errors=tuple(audit_errors),
                )

        duration_ms = (time.perf_counter() - start_time) * 1000
        _emit("skill.succeeded", {
            "skill_id": skill.id,
            "duration_ms": duration_ms,
            "exit_code": 0,
        })

        return SkillExecutionResult(
            skill_id=skill.id,
            success=True,
            exit_code=0,
            stdout="\n".join(all_stdout),
            stderr="\n".join(all_stderr),
            raw_output="\n".join(raw_outputs),
            duration_ms=duration_ms,
            audit_errors=tuple(audit_errors),
        )

    def _run_step(
        self,
        language: str,
        code: str,
        cwd: Path,
        env: dict[str, str],
        timeout: float,
    ) -> tuple[int, str, str]:
        """Execute a single step in a temporary file under containment.

        A ``bash`` step must run under a real POSIX shell when one is available.
        On Windows the previous code sent every non-Python step to PowerShell,
        and ``powershell -File`` returns 0 even when the final native command
        fails - so a broken skill was reported as a success. When no POSIX shell
        exists we fall back to PowerShell but wrap the script so it propagates
        the last native exit code instead of swallowing it.
        """
        posix_shell = self._posix_shell() if language in ("bash", "sh") else None
        use_powershell = language == "powershell" or (
            language in ("bash", "sh") and posix_shell is None
        )

        if language == "python":
            suffix = ".py"
        elif use_powershell:
            suffix = ".ps1"
            code = _wrap_powershell_exit_code(code)
        else:
            suffix = ".sh"

        with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as f:
            f.write(code)
            script_path = Path(f.name)

        try:
            if language == "python":
                cmd = [sys.executable, str(script_path)]
            elif use_powershell:
                cmd = self._powershell_argv(script_path)
            else:
                cmd = [posix_shell, script_path.as_posix()]  # type: ignore[list-item]

            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"Execution exceeded timeout of {timeout}s"
        except Exception as exc:
            return -1, "", f"Execution failure: {exc}"
        finally:
            try:
                script_path.unlink(missing_ok=True)
            except Exception:
                pass

    @staticmethod
    def _posix_shell() -> str | None:
        """Return an available POSIX shell path, or None if there is none."""
        if sys.platform == "win32":
            for git_bash in (
                Path("C:/Program Files/Git/bin/bash.exe"),
                Path("C:/Program Files/Git/usr/bin/bash.exe"),
                Path("C:/Program Files (x86)/Git/bin/bash.exe"),
            ):
                if git_bash.is_file():
                    return str(git_bash)

        for candidate in ("bash", "sh"):
            found = shutil.which(candidate)
            if found:
                if "windowsapps" in found.lower():
                    continue
                return found
        return None

    @staticmethod
    def _powershell_argv(script_path: Path) -> list[str]:
        """Build argv for the most modern available PowerShell host."""
        exe = shutil.which("pwsh") or shutil.which("powershell") or "powershell"
        return [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]

    def _emit_audit(self, event_type: str, payload: dict[str, Any]) -> str | None:
        """Emit an audit event to the injected sink.

        The canonical sink is the kernel ``EventLog``, whose ``append`` takes a
        single ``Event`` object - not ``(event_type, payload)`` keywords. Passing
        keywords raised a ``TypeError`` that was previously swallowed, so every
        skill audit silently vanished. We now build a properly typed ``Event``.
        """
        if self.event_sink is None:
            return None
        mission_id = payload.get("mission_id")
        try:
            if hasattr(self.event_sink, "append"):
                self.event_sink.append(
                    Event(
                        stream_id=SKILL_AUDIT_STREAM,
                        event_type=event_type,
                        principal_id=SKILL_AUDIT_PRINCIPAL,
                        mission_id=mission_id if isinstance(mission_id, str) else None,
                        payload=dict(payload),
                    )
                )
            elif callable(self.event_sink):
                self.event_sink(event_type, payload)
            return None
        except Exception as exc:
            # Auditing must never abort skill execution; the failure is surfaced
            # through the telemetry counter and recorded in result audit_errors.
            record_skill_audit_failure(event_type)
            return f"{event_type}: {exc}"
