---
name: netadmin-redis-monitor
description: Monitor Redis memory usage, key count, and hit rates.
---

# Redis Server Monitor Skill

## Purpose
Monitor Redis memory usage, key count, and hit rates.

## When to Activate
Activate when the user asks to:
- Redis monitor
- Redis stats
- cache performance
- Redis info

## Core Workflows

```python
import redis; r.info('memory'); r.info('stats'); r.dbsize()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
