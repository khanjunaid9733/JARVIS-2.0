---
name: desktop-launch-app
description: Open any installed Windows application by name or path.
---

# Launch Application Skill

## Purpose
Open any installed Windows application by name or path.

## When to Activate
Activate when the user asks to:
- open <app>
- launch <app>
- start <app>

## Core Workflows

```powershell
Start-Process '<AppName>'
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
