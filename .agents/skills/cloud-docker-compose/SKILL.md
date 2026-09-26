---
name: cloud-docker-compose
description: Start, stop, and rebuild Docker Compose stacks.
---

# Docker Compose Manager Skill

## Purpose
Start, stop, and rebuild Docker Compose stacks.

## When to Activate
Activate when the user asks to:
- docker compose up
- start compose
- rebuild services

## Core Workflows

```bash
docker compose up -d --build
docker compose down
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
