---
name: desktop-sleep-shutdown
description: Put the PC to sleep, hibernate, shut down, or restart.
---

# Sleep / Shutdown / Restart Skill

## Purpose
Put the PC to sleep, hibernate, shut down, or restart.

## When to Activate
Activate when the user asks to:
- sleep
- hibernate
- shutdown
- restart computer

## Core Workflows

```powershell
Stop-Computer -Force  # or Restart-Computer
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
