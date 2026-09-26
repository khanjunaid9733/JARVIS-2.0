---
name: sysdiag-disk-health
description: Check hard drive health using SMART data.
---

# Disk Health (SMART) Skill

## Purpose
Check hard drive health using SMART data.

## When to Activate
Activate when the user asks to:
- disk health
- SMART status
- hard drive health

## Core Workflows

Run `smartctl -a /dev/sdX` via subprocess or PowerShell Get-PhysicalDisk.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
