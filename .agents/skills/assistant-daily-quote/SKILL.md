---
name: assistant-daily-quote
description: Deliver a daily motivational quote or stoic philosophy.
---

# Daily Inspiration Skill

## Purpose
Deliver a daily motivational quote or stoic philosophy.

## When to Activate
Activate when the user asks to:
- motivational quote
- inspire me
- daily quote
- stoic quote

## Core Workflows

Fetch from ZenQuotes API or Quotable API, personalize to user's context.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
