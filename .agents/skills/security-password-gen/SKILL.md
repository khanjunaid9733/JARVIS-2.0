---
name: security-password-gen
description: Generate strong random passwords with configurable complexity.
---

# Password Generator Skill

## Purpose
Generate strong random passwords with configurable complexity.

## When to Activate
Activate when the user asks to:
- generate password
- create strong password
- random password

## Core Workflows

```python
import secrets, string; ''.join(secrets.choice(string.printable[:94]) for _ in range(24))
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
