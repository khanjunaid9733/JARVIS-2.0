---
name: security-port-scan
description: Scan a host for open TCP ports.
---

# Port Scanner Skill

## Purpose
Scan a host for open TCP ports.

## When to Activate
Activate when the user asks to:
- scan ports
- open ports on <host>
- port scan <ip>

## Core Workflows

```python
import socket; socket.connect(('<host>', port))  # iterate ports
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
