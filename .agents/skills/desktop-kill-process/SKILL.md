---
name: desktop-kill-process
description: Terminate any running process by name or PID.
---

# Kill Process Skill

## Purpose
Terminate any running process by name or PID.

## When to Activate
Activate when the user asks to:
- kill <process>
- close <app>
- terminate <process>

## Core Workflows

```powershell
Stop-Process -Name '<Name>' -Force
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
