---
name: sysdiag-cpu
description: Report current CPU usage, per-core load, and top consumers.
---

# CPU Usage Monitor Skill

## Purpose
Report current CPU usage, per-core load, and top consumers.

## When to Activate
Activate when the user asks to:
- CPU usage
- what's using CPU
- CPU load

## Core Workflows

```python
import psutil; psutil.cpu_percent(percpu=True)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
