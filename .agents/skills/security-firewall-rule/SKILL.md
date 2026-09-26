---
name: security-firewall-rule
description: Add or remove Windows Firewall rules for specific ports and apps.
---

# Firewall Rule Manager Skill

## Purpose
Add or remove Windows Firewall rules for specific ports and apps.

## When to Activate
Activate when the user asks to:
- block port
- allow <app> through firewall
- add firewall rule

## Core Workflows

```powershell
New-NetFirewallRule -DisplayName '<name>' -Direction Inbound -Action Block -LocalPort <port>
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
