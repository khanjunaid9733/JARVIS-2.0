"""Skill Execution Dispatcher: admission, containment, and audit.

Executes declared skill workflow steps as child processes with timeout
enforcement, output capture, and failure isolation.

What "containment" means here, precisely (`CONTAINMENT_BOUNDARY`): process
containment only. The child gets a default-deny environment, a kill-on-close
Job Object on Windows or its own process group on POSIX (terminated as a whole
tree on timeout), a timeout, and `workspace` as its working directory. It does
NOT get a filesystem, network, or registry jail. The previous docstring called
this "strict path jailing", which was not true: nothing prevented a step from
reading or writing outside `workspace`. Safety rests on execution admission
(`admission.py`, default-deny) plus the code being reviewed before it is
admitted.
"""

from __future__ import annotations

import ast
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from jarvis.kernel.event_log import Event

from .admission import SkillAdmissionPolicy, load_policy
from .context import SkillExecutionContext
from .health import HealthStatus, SkillHealthChecker
from .manifest import EXECUTABLE_LANGUAGES, SkillManifest
from .telemetry import record_skill_audit_failure

# Imported from the sub-module, not the `orchestrator` package: the package
# `__init__` pulls in mission_runner/supervisor and would re-enter this import
# chain. Same reason as the comment in live_dispatch.py.
from jarvis.orchestrator.bridges.process import TIMEOUT_EXIT_CODE, ContainedProcess

logger = logging.getLogger(__name__)

SKILL_AUDIT_STREAM = "skills"
SKILL_AUDIT_PRINCIPAL = "skills.dispatcher"

#: What the containment here actually is, stated so nobody has to guess.
#: A dispatched step runs in a child process that is:
#:   - given a default-deny environment (see `build_skill_env`),
#:   - placed in a kill-on-close Job Object (Windows) or its own process group
#:     (POSIX), and terminated as a whole TREE on timeout,
#:   - time-boxed, output-capped, and run with no shell,
#:   - given `workspace` as its working directory.
#: It is NOT a filesystem, network, or registry jail. A step can still read and
#: write outside `workspace` and still open sockets. Execution is bounded by the
#: admission allowlist (S4) and by the fact that a skill's code must be reviewed
#: and admitted - not by an OS-level sandbox.
CONTAINMENT_BOUNDARY = (
    "process containment: job-object/process-group, tree kill on timeout, "
    "default-deny env, timeout and output caps. NOT a filesystem, network, or "
    "registry jail."
)

#: Languages the dispatcher can actually run. `sh` is admitted alongside the
#: manifest set for skills that already declare it explicitly.
DISPATCHABLE_LANGUAGES: frozenset[str] = EXECUTABLE_LANGUAGES | {"sh"}

#: Environment variables a dispatched step may inherit from the parent process
#: (ADR-011 S3). Inheriting all of `os.environ` handed every skill every secret
#: the operator had exported: model API keys, cloud tokens, `JARVIS_MODEL_API_KEY`.
#: The child is now built from an explicit base plus this allowlist.
#:
#: The base keys are the minimum Windows/POSIX needs to resolve a shell and a
#: temp path. Everything else must be declared by the skill or by the caller
#: through `SkillExecutionContext.env_overrides`.
INHERITED_ENV_ALLOWLIST: frozenset[str] = frozenset(
    {
        # shell / interpreter resolution
        "COMSPEC",
        "SYSTEMROOT",
        "SYSTEMDRIVE",
        "WINDIR",
        "PATHEXT",
        "PATH",
        # POSIX shells (git-bash / WSL shims) still honor these
        "HOME",
        "SHELL",
        "LANG",
        "LC_ALL",
        "TMPDIR",
        "TEMP",
        "TMP",
        # locale/encoding correctness for subprocess IO
        "PYTHONUTF8",
        "PYTHONIOENCODING",
        # terminal width/height for help text and pagers
        "COLUMNS",
        "LINES",
    }
)

#: Prefixes for env vars that are inherited wholesale (case-insensitive on
#: Windows). Used for narrowly scoped families, e.g. proxy configuration.
INHERITED_ENV_PREFIXES: tuple[str, ...] = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "no_proxy",
)


def build_skill_env(
    overrides: Mapping[str, str] | None = None,
    *,
    source_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the environment for a dispatched skill step.

    ADR-011 S3: default-deny inheritance. Only `INHERITED_ENV_ALLOWLIST` and
    `INHERITED_ENV_PREFIXES` are copied from the parent environment; every other
    variable (API keys, tokens, unrelated config) is withheld. Explicit
    `overrides` are applied last so a caller can still pass through a specific
    value deliberately.

    `source_env` exists for tests; production passes the real `os.environ`.
    """
    parent = os.environ if source_env is None else source_env

    env: dict[str, str] = {}
    for key, value in parent.items():
        if key.upper() in INHERITED_ENV_ALLOWLIST or key in INHERITED_ENV_PREFIXES:
            env[key] = value

    # Guarantee UTF-8 regardless of what the parent set or omitted.
    env["PYTHONUTF8"] = "1"

    for key, value in (overrides or {}).items():
        env[str(key)] = str(value)

    return env


def _wrap_powershell_exit_code(code: str) -> str:
    """Append propagation of the last native exit code to a PowerShell script.

    Without this, ``powershell -File`` exits 0 no matter how the final native
    command failed, turning a failed skill into a reported success.
    """
    return (
        code
        + "\nif ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n"
    )


def _auto_print_expression(code: str) -> str:
    """If code ends with an evaluable expression (not an assignment or print),
    append printing of that expression so CLI and callers receive the result."""
    try:
        tree = ast.parse(code)
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            val = tree.body[-1].value
            if isinstance(val, ast.Call) and getattr(val.func, "id", None) == "print":
                return code
            lines = code.splitlines()
            if lines:
                last_line = lines[-1]
                parts = [p.strip() for p in last_line.split(";") if p.strip()]
                expr = parts[-1] if parts else last_line
                return f"{code}\n__res__ = {expr}\nif __res__ is not None:\n    print(__res__)"
    except Exception:
        pass
    return code


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
    """Dispatches skill executions with safety gates, timeouts, and auditing.

    `admission` is the default-deny execution allowlist (ADR-011 S4). Passing
    `None` resolves the on-disk/env policy; pass
    `SkillAdmissionPolicy(entries=frozenset())` to deny everything, or an
    explicit policy to run in tests. Discovery is unaffected: a skill that is
    refused here is still listed, findable and inspectable.
    """

    def __init__(
        self,
        health_checker: HealthStatus | None = None,
        event_sink: Any | None = None,
        admission: SkillAdmissionPolicy | None = None,
    ) -> None:
        self.health_checker = health_checker or SkillHealthChecker()
        self.event_sink = event_sink
        self.admission = load_policy() if admission is None else admission

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

        # 0. Execution admission (ADR-011 S4). Default-deny: a skill that is not
        # on the allowlist is refused here, before any subprocess is created.
        # Discovery/search/inspect are unaffected, so the library stays
        # browsable while only reviewed skills can execute.
        #
        # A dry run is exempt, matching the health gate below: it creates no
        # subprocess and only renders the declared steps, so previewing an
        # unadmitted skill leaks nothing and is how an operator decides whether
        # to admit it.
        if not context.dry_run and not self.admission.is_admitted(skill.id):
            duration_ms = (time.perf_counter() - start_time) * 1000
            reason = (
                f"skill '{skill.id}' is not on the execution allowlist; "
                f"admit it with `jarvis skill admit {skill.id}` "
                f"(currently admitted: {len(self.admission.admitted_ids())})"
            )
            _emit("skill.refused", {
                "skill_id": skill.id,
                "mission_id": context.mission_id,
                "reason": reason,
                "refusal_stage": "admission",
            })
            return SkillExecutionResult(
                skill_id=skill.id,
                success=False,
                exit_code=-1,
                refusal_reason=reason,
                duration_ms=duration_ms,
                audit_errors=tuple(audit_errors),
            )

        # 0b. Content pin (ADR-011 S4). Being on the allowlist is not enough if
        # the file changed after review: the agent can rewrite any file, so an
        # id-only allowlist would be revocable the instant a skill is admitted.
        # An entry recorded by `jarvis skill admit` carries a sha256 of the
        # reviewed bytes; if they no longer match, refuse. Same pre-subprocess
        # position as the allowlist check above.
        if not context.dry_run:
            content_reason = self.admission.check_content(skill.id, skill.source_path)
            if content_reason:
                duration_ms = (time.perf_counter() - start_time) * 1000
                _emit("skill.refused", {
                    "skill_id": skill.id,
                    "mission_id": context.mission_id,
                    "reason": content_reason,
                    "refusal_stage": "admission_content_pin",
                })
                return SkillExecutionResult(
                    skill_id=skill.id,
                    success=False,
                    exit_code=-1,
                    refusal_reason=content_reason,
                    duration_ms=duration_ms,
                    audit_errors=tuple(audit_errors),
                )

        # 1. Deterministic Precondition Health Check
        health = self.health_checker.evaluate(skill)
        if not health.is_executable and not context.dry_run:
            duration_ms = (time.perf_counter() - start_time) * 1000
            _emit("skill.refused", {
                "skill_id": skill.id,
                "mission_id": context.mission_id,
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

        # 2. Check if skill is runnable.
        # Admission is per-step and driven by the step's own explicit language
        # tag (ADR-011 S1). `sh` stays admitted for backward compatibility with
        # skills that already tag it. Untagged fences now parse as `text` and
        # are therefore excluded here, so documentation prose is never executed.
        executable_steps = [
            s for s in skill.workflow_steps
            if s.language in DISPATCHABLE_LANGUAGES and s.code.strip()
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

        # Build execution environment: default-deny inheritance (ADR-011 S3).
        env = build_skill_env(context.env_overrides)

        context.workspace.mkdir(parents=True, exist_ok=True)

        for step in executable_steps:
            code_text = context.substitute_params(step.code)
            if step.language == "python":
                preamble_parts: list[str] = []
                if context.parameters:
                    for k, v in context.parameters.items():
                        if k.isidentifier():
                            preamble_parts.append(f"{k} = {repr(v)}")

                # Auto-import common modules if referenced without explicit import
                common_modules = (
                    "psutil", "os", "sys", "json", "math", "re", "shutil",
                    "pathlib", "datetime", "subprocess", "time",
                )
                for mod in common_modules:
                    if re.search(rf"\b{mod}\b", code_text) and not re.search(rf"\b(?:import|from)\s+{mod}\b", code_text):
                        preamble_parts.append(f"try:\n    import {mod}\nexcept ImportError:\n    pass")

                if preamble_parts:
                    code_text = "\n".join(preamble_parts) + "\n" + code_text

                code_text = _auto_print_expression(code_text)
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
                    "mission_id": context.mission_id,
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
            "mission_id": context.mission_id,
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

            # ADR-011 S5: run through the existing containment seam instead of
            # a bare `subprocess.run`. `ContainedProcess` puts the child in a
            # kill-on-close Job Object (Windows) or its own process group (POSIX)
            # and, on timeout, terminates the WHOLE descendant tree rather than
            # leaving orphaned grandchildren behind. It is still only process
            # containment: it does not jail the filesystem, so a step can still
            # read and write outside `workspace`. See CONTAINMENT_BOUNDARY.
            proc = ContainedProcess(cmd, cwd, env=env)
            exit_code, stdout, stderr = proc.start().wait(timeout=timeout)
            if exit_code == TIMEOUT_EXIT_CODE:
                return (
                    exit_code,
                    stdout,
                    stderr + f"\nExecution exceeded timeout of {timeout}s; "
                    "the process tree was terminated",
                )
            return exit_code, stdout, stderr
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
            # Auditing must not abort skill execution: a locked or full log
            # should not make the whole skill library unusable. But the failure
            # must not be invisible either, or "the ledger has no record" is
            # indistinguishable from "nothing happened". So: count it, log it,
            # and hand it back on the result for the caller to surface.
            record_skill_audit_failure(event_type)
            logger.warning("Skill audit write failed for %s: %s", event_type, exc)
            return f"{event_type}: {exc}"
