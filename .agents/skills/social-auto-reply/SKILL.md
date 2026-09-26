---
name: social-auto-reply
description: Draft responses to comments and DMs automatically.
---

# Social Auto-Responder Skill

## Purpose
Draft responses to comments and DMs automatically.

## When to Activate
Activate when the user asks to:
- reply to comments
- auto respond
- draft replies

## Core Workflows

Classify comment intent, route through LLM for personalized draft reply.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
