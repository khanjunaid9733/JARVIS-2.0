---
name: dev-code-format
description: Auto-format Python, JS, or other code with Black, Prettier, or ruff.
---

# Code Formatter Skill

## Purpose
Auto-format Python, JS, or other code with Black, Prettier, or ruff.

## When to Activate
Activate when the user asks to:
- format code
- run black
- auto-format
- lint and fix

## Core Workflows

```bash
python -m black src/ tests/
# or
npx prettier --write '**/*.js'
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
