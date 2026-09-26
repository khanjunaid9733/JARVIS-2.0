---
name: dev-run-tests
description: Execute pytest, unittest, or jest test suites and report results.
---

# Run Test Suite Skill

## Purpose
Execute pytest, unittest, or jest test suites and report results.

## When to Activate
Activate when the user asks to:
- run tests
- execute test suite
- pytest
- run unit tests

## Core Workflows

```bash
python -m pytest tests/ -v --tb=short
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
