---
name: sysdiag-disk
description: Show disk space usage per drive and partition.
---

# Disk Usage Skill

## Purpose
Show disk space usage per drive and partition.

## When to Activate
Activate when the user asks to:
- disk space
- how full is drive C
- storage left

## Core Workflows

```python
psutil.disk_usage('/')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
