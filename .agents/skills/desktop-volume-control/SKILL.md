---
name: desktop-volume-control
description: Set, increase, decrease, or mute system audio volume.
---

# Volume Control Skill

## Purpose
Set, increase, decrease, or mute system audio volume.

## When to Activate
Activate when the user asks to:
- set volume to X%
- mute
- unmute
- volume up
- volume down

## Core Workflows

Use `nircmd.exe setsysvolume <0-65535>` or PowerShell SendKeys for volume keys.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
