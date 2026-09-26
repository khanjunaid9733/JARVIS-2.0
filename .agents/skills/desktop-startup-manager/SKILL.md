---
name: desktop-startup-manager
description: Add or remove programs from Windows startup.
---

# Startup Program Manager Skill

## Purpose
Add or remove programs from Windows startup.

## When to Activate
Activate when the user asks to:
- add to startup
- remove from startup
- list startup programs

## Core Workflows

Modify `HKCU:\Software\Microsoft\Windows\CurrentVersion\Run` via PowerShell.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
