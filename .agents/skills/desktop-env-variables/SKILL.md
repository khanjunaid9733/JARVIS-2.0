---
name: desktop-env-variables
description: Get, set, or delete Windows environment variables.
---

# Environment Variables Skill

## Purpose
Get, set, or delete Windows environment variables.

## When to Activate
Activate when the user asks to:
- set environment variable
- read env var
- delete env

## Core Workflows

```powershell
[System.Environment]::SetEnvironmentVariable('KEY','VALUE','User')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
