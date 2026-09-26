---
name: desktop-accessibility
description: Toggle accessibility features: high contrast, narrator, magnifier, sticky keys.
---

# Accessibility Tools Skill

## Purpose
Toggle accessibility features: high contrast, narrator, magnifier, sticky keys.

## When to Activate
Activate when the user asks to:
- enable high contrast
- toggle narrator
- magnify screen

## Core Workflows

Use `SystemParametersInfo` via ctypes or PowerShell `Set-Accessibility`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
