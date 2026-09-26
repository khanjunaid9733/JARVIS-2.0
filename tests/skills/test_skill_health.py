from __future__ import annotations

import pytest

from jarvis.skills.health import HealthStatus, SkillHealthChecker
from jarvis.skills.manifest import parse_skill_markdown


def test_health_checker_healthy_skill():
    doc = """---
name: basic-echo
description: Echo test skill using built-in commands.
---
# Echo Skill
## Core Workflows
```bash
echo "hello"
```
"""
    skill = parse_skill_markdown(doc)
    # Clear out any accidental binaries
    skill.prerequisites.required_binaries.clear()
    skill.prerequisites.required_env_vars.clear()
    skill.prerequisites.required_python_modules.clear()

    checker = SkillHealthChecker(env={})
    report = checker.evaluate(skill)
    assert report.status == HealthStatus.HEALTHY
    assert report.is_executable is True
    assert len(report.missing_binaries) == 0


def test_health_checker_missing_binary():
    doc = """---
name: custom-tool
description: Tool requiring hypothetical non-existent binary.
---
# Custom Tool
## Core Workflows
```bash
nonexistent_quantum_cli_binary_xyz --run
```
"""
    skill = parse_skill_markdown(doc)
    skill.prerequisites.required_binaries.append("nonexistent_quantum_cli_binary_xyz")

    checker = SkillHealthChecker(env={})
    report = checker.evaluate(skill)
    assert report.status == HealthStatus.UNAVAILABLE
    assert report.is_executable is False
    assert "nonexistent_quantum_cli_binary_xyz" in report.missing_binaries
    assert "nonexistent_quantum_cli_binary_xyz" in report.summary


def test_health_checker_missing_env_var():
    doc = """---
name: cloud-service
description: Cloud tool requiring API key.
---
# Cloud Service
## Core Workflows
```bash
curl -H "Authorization: Bearer $SOME_UNIQUE_TEST_KEY" https://api.example.com
```
"""
    skill = parse_skill_markdown(doc)
    skill.prerequisites.required_binaries.clear()
    skill.prerequisites.required_env_vars = ["SOME_UNIQUE_TEST_KEY"]

    checker = SkillHealthChecker(env={})
    report = checker.evaluate(skill)
    assert report.status == HealthStatus.DEGRADED
    assert report.is_executable is False
    assert "SOME_UNIQUE_TEST_KEY" in report.missing_env_vars

    # Now provide the env var
    checker_with_env = SkillHealthChecker(env={"SOME_UNIQUE_TEST_KEY": "valid_token_123"})
    report2 = checker_with_env.evaluate(skill)
    assert report2.status == HealthStatus.HEALTHY
    assert report2.is_executable is True
