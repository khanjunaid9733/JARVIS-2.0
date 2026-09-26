---
name: language-etymology
description: Trace the origin and historical evolution of any word.
---

# Word Etymology Skill

## Purpose
Trace the origin and historical evolution of any word.

## When to Activate
Activate when the user asks to:
- word origin
- etymology of
- where does word come from
- history of word

## Core Workflows

Prompt: `Trace the etymology of '{word}': language of origin, root meaning, historical evolution, first recorded use.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
