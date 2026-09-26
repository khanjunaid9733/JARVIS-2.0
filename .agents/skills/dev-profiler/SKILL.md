---
name: dev-profiler
description: Profile Python code execution time and memory usage.
---

# Python Profiler Skill

## Purpose
Profile Python code execution time and memory usage.

## When to Activate
Activate when the user asks to:
- profile <script>
- measure performance
- benchmark

## Core Workflows

```python
import cProfile; cProfile.run('module.function()')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
