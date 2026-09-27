"""ADR-011 S3 regression tests: environment containment.

The dispatcher used to build the child environment with `env = dict(os.environ)`,
so every dispatched skill inherited every secret the operator had exported -
`JARVIS_MODEL_API_KEY`, cloud tokens, and anything else in the session.

Admission is now default-deny: only an explicit allowlist (plus caller-declared
overrides) reaches a skill step.
"""

from __future__ import annotations

from pathlib import Path

from jarvis.skills.context import SkillExecutionContext
from jarvis.skills.dispatcher import (
    INHERITED_ENV_ALLOWLIST,
    build_skill_env,
)

SECRETS = {
    "JARVIS_MODEL_API_KEY": "sk-super-secret",
    "AWS_SECRET_ACCESS_KEY": "aws-secret",
    "GITHUB_TOKEN": "ghp_secret",
    "AZURE_CLIENT_SECRET": "azure-secret",
    "DATABASE_URL": "postgres://user:pw@host/db",
    "SSH_AUTH_SOCK": "/tmp/agent.sock",
}

SAFE = {
    "PATH": r"C:\Windows\system32",
    "SYSTEMROOT": r"C:\Windows",
    "COMSPEC": r"C:\Windows\system32\cmd.exe",
    "TEMP": r"C:\Temp",
    "HTTP_PROXY": "http://proxy:8080",
}


def _parent() -> dict[str, str]:
    return {**SAFE, **SECRETS}


def test_secrets_are_not_inherited() -> None:
    env = build_skill_env(source_env=_parent())
    for name, value in SECRETS.items():
        assert name not in env, f"{name} leaked into the skill environment"


def test_allowlisted_vars_are_inherited() -> None:
    env = build_skill_env(source_env=_parent())
    for name, value in SAFE.items():
        assert env.get(name) == value


def test_proxy_prefix_is_inherited() -> None:
    env = build_skill_env(source_env=_parent())
    assert env.get("HTTP_PROXY") == "http://proxy:8080"


def test_case_insensitive_allowlist_on_windows_names() -> None:
    env = build_skill_env(source_env={"path": "custom-path", "systemroot": "root"})
    assert env.get("path") == "custom-path"
    assert env.get("systemroot") == "root"


def test_utf8_is_always_set() -> None:
    env = build_skill_env(source_env={})
    assert env["PYTHONUTF8"] == "1"


def test_overrides_are_applied_and_can_deliberately_pass_a_secret() -> None:
    """A caller can still pass a specific value on purpose; that is explicit."""
    env = build_skill_env(
        {"JARVIS_MODEL_API_KEY": "deliberate", "EXTRA": "1"}, source_env=_parent()
    )
    assert env["JARVIS_MODEL_API_KEY"] == "deliberate"
    assert env["EXTRA"] == "1"


def test_overrides_win_over_parent_value() -> None:
    env = build_skill_env({"TEMP": r"D:\other"}, source_env=_parent())
    assert env["TEMP"] == r"D:\other"


def test_no_unrelated_parent_keys_leak_through() -> None:
    env = build_skill_env(source_env=_parent())
    assert set(env) - set(INHERITED_ENV_ALLOWLIST) <= {
        "HTTP_PROXY",  # prefix-allowed
        "PYTHONUTF8",  # forced
    }


def test_context_env_overrides_flow_into_builder() -> None:
    ctx = SkillExecutionContext(
        workspace=Path("."), env_overrides={"SKILL_TOKEN": "tok"}
    )
    env = build_skill_env(ctx.env_overrides, source_env=_parent())
    assert env["SKILL_TOKEN"] == "tok"
    assert "JARVIS_MODEL_API_KEY" not in env


def test_real_process_does_not_see_secret(tmp_path: Path) -> None:
    """End-to-end: a dispatched step cannot read a parent secret from its env."""
    import os
    import subprocess
    import sys

    script = tmp_path / "probe.py"
    script.write_text(
        "import json, os\nprint(json.dumps({k: os.environ.get(k) for k in "
        "('JARVIS_MODEL_API_KEY','GITHUB_TOKEN','PATH')}))\n",
        encoding="utf-8",
    )
    env = build_skill_env(source_env={**os.environ, **SECRETS})
    out = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert out.returncode == 0
    import json

    seen = json.loads(out.stdout)
    assert seen["JARVIS_MODEL_API_KEY"] is None
    assert seen["GITHUB_TOKEN"] is None
