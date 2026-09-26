---
name: comm-meeting-notes
description: Send formatted meeting notes to all participants after a call.
---

# Meeting Notes Sender Skill

## Purpose
Send formatted meeting notes to all participants after a call.

## When to Activate
Activate when the user asks to:
- send meeting notes
- distribute notes
- email recap

## Core Workflows

Compose structured notes from inputs, format as HTML email, send via SMTP.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
