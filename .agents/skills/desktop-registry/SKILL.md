---
name: desktop-registry
description: Read and safely write Windows Registry keys and values.
---

# Registry Editor Skill

## Purpose
Read and safely write Windows Registry keys and values.

## When to Activate
Activate when the user asks to:
- read registry key
- set registry value

## Core Workflows

```powershell
Get-ItemProperty 'HKCU:\...'; Set-ItemProperty ...
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
