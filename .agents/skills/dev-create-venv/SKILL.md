---
name: dev-create-venv
description: Create and activate a Python virtual environment.
---

# Virtual Environment Creator Skill

## Purpose
Create and activate a Python virtual environment.

## When to Activate
Activate when the user asks to:
- create venv
- setup python env
- create virtualenv

## Core Workflows

```bash
python -m venv .venv && .venv\Scripts\activate
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
