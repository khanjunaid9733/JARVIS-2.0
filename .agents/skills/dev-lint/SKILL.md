---
name: dev-lint
description: Run linting checks on code and report issues.
---

# Linter Skill

## Purpose
Run linting checks on code and report issues.

## When to Activate
Activate when the user asks to:
- lint code
- check code quality
- run flake8
- eslint

## Core Workflows

```bash
python -m ruff check src/ tests/
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
