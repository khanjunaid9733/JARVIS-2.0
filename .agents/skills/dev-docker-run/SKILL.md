---
name: dev-docker-run
description: Run a Docker container with port mappings and env vars.
---

# Docker Run Skill

## Purpose
Run a Docker container with port mappings and env vars.

## When to Activate
Activate when the user asks to:
- run docker container
- start container
- docker run

## Core Workflows

```bash
docker run -d -p 8080:80 --name <name> <image>
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
