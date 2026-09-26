---
name: sysdiag-ram
description: Report used, available, and total RAM with top memory consumers.
---

# RAM Usage Monitor Skill

## Purpose
Report used, available, and total RAM with top memory consumers.

## When to Activate
Activate when the user asks to:
- RAM usage
- memory usage
- how much memory

## Core Workflows

```python
psutil.virtual_memory()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
