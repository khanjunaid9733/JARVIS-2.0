---
name: assistant-vocab-word
description: Deliver a new vocabulary word with definition and usage each day.
---

# Word of the Day Skill

## Purpose
Deliver a new vocabulary word with definition and usage each day.

## When to Activate
Activate when the user asks to:
- word of the day
- new word
- vocabulary builder
- expand vocabulary

## Core Workflows

GET Wordnik API `/word.json/{word}/definitions` for a random interesting word.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
