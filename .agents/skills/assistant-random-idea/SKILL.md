---
name: assistant-random-idea
description: Generate surprising and creative ideas on demand.
---

# Random Creative Idea Generator Skill

## Purpose
Generate surprising and creative ideas on demand.

## When to Activate
Activate when the user asks to:
- random idea
- creative idea
- inspire me
- give me an idea

## Core Workflows

Prompt: `Generate a surprising, creative, and actionable idea for {domain}. Make it specific and original.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
