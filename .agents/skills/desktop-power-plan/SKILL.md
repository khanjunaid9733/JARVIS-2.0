---
name: desktop-power-plan
description: Switch Windows power plans (Balanced, Performance, Power Saver).
---

# Power Plan Manager Skill

## Purpose
Switch Windows power plans (Balanced, Performance, Power Saver).

## When to Activate
Activate when the user asks to:
- switch to performance mode
- enable battery saver
- set power plan

## Core Workflows

```powershell
powercfg /setactive SCHEME_MIN  # High Performance
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
