---
name: sysdiag-firewall
description: Check Windows Defender Firewall status and rules.
---

# Firewall Status Skill

## Purpose
Check Windows Defender Firewall status and rules.

## When to Activate
Activate when the user asks to:
- firewall status
- is firewall on
- firewall rules

## Core Workflows

```powershell
Get-NetFirewallProfile | Select Name, Enabled
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
