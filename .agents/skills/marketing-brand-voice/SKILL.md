---
name: marketing-brand-voice
description: Define and document a brand's voice, tone, and style guidelines.
---

# Brand Voice Guide Skill

## Purpose
Define and document a brand's voice, tone, and style guidelines.

## When to Activate
Activate when the user asks to:
- brand voice
- brand tone
- style guide
- brand identity

## Core Workflows

Prompt: `Create a brand voice guide for {brand} in {industry}. Define: personality, tone, do's/don'ts, examples.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
