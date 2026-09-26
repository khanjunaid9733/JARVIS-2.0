---
name: desktop-multi-monitor
description: Move windows across monitors, set display layout, and change resolution.
---

# Multi-Monitor Control Skill

## Purpose
Move windows across monitors, set display layout, and change resolution.

## When to Activate
Activate when the user asks to:
- move to monitor 2
- set resolution
- change display

## Core Workflows

Use PowerShell `Set-DisplayResolution` or `DisplaySwitch.exe`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
