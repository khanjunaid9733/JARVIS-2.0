---
name: sysdiag-boot-time
description: Show how long the system has been running since last boot.
---

# System Uptime Skill

## Purpose
Show how long the system has been running since last boot.

## When to Activate
Activate when the user asks to:
- system uptime
- how long since restart
- boot time

## Core Workflows

```python
import datetime; datetime.datetime.fromtimestamp(psutil.boot_time())
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
