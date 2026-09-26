---
name: dev-docker-build
description: Build a Docker image from a Dockerfile.
---

# Docker Build Skill

## Purpose
Build a Docker image from a Dockerfile.

## When to Activate
Activate when the user asks to:
- build docker image
- docker build
- create container image

## Core Workflows

```bash
docker build -t <image>:<tag> .
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
