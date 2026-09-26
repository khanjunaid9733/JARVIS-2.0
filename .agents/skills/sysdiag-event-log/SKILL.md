---
name: sysdiag-event-log
description: Read and filter Windows Event Log entries.
---

# Windows Event Log Reader Skill

## Purpose
Read and filter Windows Event Log entries.

## When to Activate
Activate when the user asks to:
- check event log
- windows errors
- application log
- system log

## Core Workflows

```powershell
Get-EventLog -LogName Application -Newest 20 -EntryType Error
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
