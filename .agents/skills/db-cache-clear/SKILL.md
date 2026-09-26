---
name: db-cache-clear
description: Clear Redis or Memcached cache entries.
---

# Cache Flush Skill

## Purpose
Clear Redis or Memcached cache entries.

## When to Activate
Activate when the user asks to:
- clear cache
- flush Redis
- invalidate cache

## Core Workflows

```python
r.flushdb()  # Redis
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
