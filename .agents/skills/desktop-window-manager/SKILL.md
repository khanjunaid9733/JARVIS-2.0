---
name: desktop-window-manager
description: Minimize, maximize, restore, move, and resize application windows.
---

# Window Manager Skill

## Purpose
Minimize, maximize, restore, move, and resize application windows.

## When to Activate
Activate when the user asks to:
- minimize <app>
- maximize <app>
- resize window
- move window

## Core Workflows

Use Windows UIA (UIAutomation COM) or `AutoHotkey` scripts dispatched via subprocess.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
