---
name: language-tongue-twister
description: Create phonetically challenging tongue twisters.
---

# Tongue Twister Generator Skill

## Purpose
Create phonetically challenging tongue twisters.

## When to Activate
Activate when the user asks to:
- tongue twister
- phonetics practice
- difficult to say

## Core Workflows

Prompt: `Create a tongue twister using {sound} sounds that's challenging but repeatable.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
