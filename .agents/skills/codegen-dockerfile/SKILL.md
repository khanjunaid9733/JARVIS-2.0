---
name: codegen-dockerfile
description: Generate optimized Dockerfiles for any application.
---

# Dockerfile Generator Skill

## Purpose
Generate optimized Dockerfiles for any application.

## When to Activate
Activate when the user asks to:
- Dockerfile
- containerize app
- Docker image
- create Dockerfile

## Core Workflows

Generate multi-stage Dockerfile with minimal base image, layer caching, security best practices.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
