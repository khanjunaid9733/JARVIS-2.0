---
name: writing-email-draft
description: Draft professional, friendly, or formal emails for any situation.
---

# Email Drafter Skill

## Purpose
Draft professional, friendly, or formal emails for any situation.

## When to Activate
Activate when the user asks to:
- draft email
- write email to
- compose email
- email about

## Core Workflows

Prompt: `Draft a {tone} email to {recipient} about {subject}. Keep it {length}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
