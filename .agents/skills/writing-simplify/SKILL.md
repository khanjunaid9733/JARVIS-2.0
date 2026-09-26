---
name: writing-simplify
description: Rewrite complex text in simple, easy-to-understand language.
---

# Text Simplifier Skill

## Purpose
Rewrite complex text in simple, easy-to-understand language.

## When to Activate
Activate when the user asks to:
- simplify
- explain simply
- easy language
- simplify for kids

## Core Workflows

Prompt: `Rewrite the following for a general audience at a 6th-grade reading level: {text}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
