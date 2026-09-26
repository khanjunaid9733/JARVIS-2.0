---
name: netadmin-docker-manage
description: List, start, stop, and inspect running Docker containers.
---

# Docker Container Manager Skill

## Purpose
List, start, stop, and inspect running Docker containers.

## When to Activate
Activate when the user asks to:
- docker containers
- list containers
- docker ps
- container status

## Core Workflows

```bash
docker ps -a; docker stats; docker logs <container>
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
