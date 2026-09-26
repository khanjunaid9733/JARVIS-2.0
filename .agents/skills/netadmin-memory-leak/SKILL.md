---
name: netadmin-memory-leak
description: Identify processes with growing memory footprints.
---

# Memory Leak Detector Skill

## Purpose
Identify processes with growing memory footprints.

## When to Activate
Activate when the user asks to:
- memory leak
- RAM growing
- process memory
- memory debug

## Core Workflows

```python
for p in psutil.process_iter(['name','memory_info']): track over time
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
