---
name: sysdiag-traceroute
description: Trace the network route to a destination host.
---

# Traceroute Skill

## Purpose
Trace the network route to a destination host.

## When to Activate
Activate when the user asks to:
- traceroute to <host>
- trace path
- network hops to <host>

## Core Workflows

```python
subprocess.run(['tracert', host], capture_output=True)  # Windows
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
