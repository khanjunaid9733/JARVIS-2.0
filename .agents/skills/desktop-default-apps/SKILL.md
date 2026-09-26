---
name: desktop-default-apps
description: Change default applications for file types and protocols.
---

# Default App Setter Skill

## Purpose
Change default applications for file types and protocols.

## When to Activate
Activate when the user asks to:
- set default browser
- change default app for .pdf

## Core Workflows

Use `assoc` and `ftype` commands or Windows Settings via `ms-settings:defaultapps`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
