---
name: desktop-hotkeys
description: Register global keyboard shortcuts that trigger JARVIS actions.
---

# Global Hotkey Registration Skill

## Purpose
Register global keyboard shortcuts that trigger JARVIS actions.

## When to Activate
Activate when the user asks to:
- set hotkey
- register shortcut
- bind key

## Core Workflows

Use `keyboard` Python library: `keyboard.add_hotkey('ctrl+shift+j', callback)`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
