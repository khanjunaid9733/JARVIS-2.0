---
name: desktop-notifications
description: Display toast notifications on the Windows desktop.
---

# Desktop Notifications Skill

## Purpose
Display toast notifications on the Windows desktop.

## When to Activate
Activate when the user asks to:
- show notification
- alert me
- pop up message

## Core Workflows

Use PowerShell `New-BurntToastNotification` or Windows Runtime Notification API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
