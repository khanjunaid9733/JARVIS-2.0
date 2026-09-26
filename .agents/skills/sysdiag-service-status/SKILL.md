---
name: sysdiag-service-status
description: Check and control Windows services (start/stop/status).
---

# Windows Service Monitor Skill

## Purpose
Check and control Windows services (start/stop/status).

## When to Activate
Activate when the user asks to:
- service status
- is <service> running
- start service
- stop service

## Core Workflows

```powershell
Get-Service -Name <ServiceName>; Start-Service -Name <ServiceName>
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
