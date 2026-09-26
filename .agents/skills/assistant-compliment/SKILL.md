---
name: assistant-compliment
description: Generate genuine, personalized compliments.
---

# Compliment Generator Skill

## Purpose
Generate genuine, personalized compliments.

## When to Activate
Activate when the user asks to:
- compliment me
- say something nice
- encourage me

## Core Workflows

Prompt: `Generate 5 genuine, specific compliments for someone who is {context}. Be warm and authentic.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
