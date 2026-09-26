---
name: cloud-scale-service
description: Manually scale up/down a containerized service.
---

# Auto-Scale Service Skill

## Purpose
Manually scale up/down a containerized service.

## When to Activate
Activate when the user asks to:
- scale to N replicas
- increase pods
- scale down

## Core Workflows

```bash
kubectl scale deployment/<name> --replicas=N
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
