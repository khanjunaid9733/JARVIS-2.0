---
name: sysdiag-network
description: Show network interfaces, bytes sent/received, and active connections.
---

# Network Stats Skill

## Purpose
Show network interfaces, bytes sent/received, and active connections.

## When to Activate
Activate when the user asks to:
- network usage
- internet speed
- bytes sent received

## Core Workflows

```python
psutil.net_io_counters(pernic=True)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
