---
name: db-redis-get-set
description: Get and set values in Redis with TTL support.
---

# Redis Key-Value Store Skill

## Purpose
Get and set values in Redis with TTL support.

## When to Activate
Activate when the user asks to:
- get from Redis
- set Redis key
- Redis cache
- store in Redis

## Core Workflows

```python
import redis; r = redis.Redis(); r.set('key', 'value', ex=3600)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
