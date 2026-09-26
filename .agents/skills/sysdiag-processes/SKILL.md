---
name: sysdiag-processes
description: List all running processes with PID, CPU, and memory usage.
---

# Process Lister Skill

## Purpose
List all running processes with PID, CPU, and memory usage.

## When to Activate
Activate when the user asks to:
- list processes
- running programs
- top processes
- show tasks

## Core Workflows

```python
for p in psutil.process_iter(['pid','name','cpu_percent']): print(p.info)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
