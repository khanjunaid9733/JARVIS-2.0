---
name: sysdiag-battery
description: Report battery percentage, charging state, and estimated time remaining.
---

# Battery Status Skill

## Purpose
Report battery percentage, charging state, and estimated time remaining.

## When to Activate
Activate when the user asks to:
- battery level
- is plugged in
- charge remaining

## Core Workflows

```python
psutil.sensors_battery()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
