---
name: desktop-font-manager
description: List, install, and remove fonts on Windows.
---

# Font Manager Skill

## Purpose
List, install, and remove fonts on Windows.

## When to Activate
Activate when the user asks to:
- install font
- list fonts
- remove font

## Core Workflows

Copy font file to `C:\Windows\Fonts` and register via Registry.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
