---
name: sysdiag-drivers
description: List installed device drivers and their statuses.
---

# Driver Lister Skill

## Purpose
List installed device drivers and their statuses.

## When to Activate
Activate when the user asks to:
- list drivers
- check driver status
- device drivers

## Core Workflows

```powershell
Get-WmiObject Win32_PnPSignedDriver | Select DeviceName, DriverVersion
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
