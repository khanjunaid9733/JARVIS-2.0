---
name: sysdiag-ping
description: Ping a host and measure round-trip latency.
---

# Ping / Latency Test Skill

## Purpose
Ping a host and measure round-trip latency.

## When to Activate
Activate when the user asks to:
- ping <host>
- check latency to <host>
- is <host> reachable

## Core Workflows

```python
subprocess.run(['ping', '-n', '4', host], capture_output=True)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
