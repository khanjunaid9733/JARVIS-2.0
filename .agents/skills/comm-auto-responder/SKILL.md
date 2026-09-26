---
name: comm-auto-responder
description: Set up automatic replies for emails or chat messages.
---

# Auto-Responder Skill

## Purpose
Set up automatic replies for emails or chat messages.

## When to Activate
Activate when the user asks to:
- set auto-reply
- out of office
- automatic response

## Core Workflows

IMAP IDLE loop + condition match + templated reply via SMTP.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
