---
name: sysdiag-open-ports
description: List all open TCP/UDP ports and the processes using them.
---

# Open Port Scanner Skill

## Purpose
List all open TCP/UDP ports and the processes using them.

## When to Activate
Activate when the user asks to:
- open ports
- what's listening on port
- network connections

## Core Workflows

```python
psutil.net_connections(kind='inet')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
