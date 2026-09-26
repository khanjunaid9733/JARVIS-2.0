---
name: desktop-lock-screen
description: Lock the Windows workstation immediately.
---

# Lock Screen Skill

## Purpose
Lock the Windows workstation immediately.

## When to Activate
Activate when the user asks to:
- lock screen
- lock computer
- secure workstation

## Core Workflows

```powershell
rundll32.exe user32.dll,LockWorkStation
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
