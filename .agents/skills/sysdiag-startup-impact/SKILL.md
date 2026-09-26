---
name: sysdiag-startup-impact
description: Report startup programs and their performance impact.
---

# Startup Impact Analyzer Skill

## Purpose
Report startup programs and their performance impact.

## When to Activate
Activate when the user asks to:
- startup impact
- boot slowdown
- startup programs performance

## Core Workflows

```powershell
Get-CimInstance Win32_StartupCommand
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
