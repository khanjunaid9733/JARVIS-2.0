---
name: desktop-taskbar
description: Pin, unpin, and interact with taskbar and system tray items.
---

# Taskbar & Tray Control Skill

## Purpose
Pin, unpin, and interact with taskbar and system tray items.

## When to Activate
Activate when the user asks to:
- pin to taskbar
- check system tray
- show tray icon

## Core Workflows

Use UIA AutomationElement to locate taskbar elements and invoke actions.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
