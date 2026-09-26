---
name: writing-poem
description: Write poems in any style: haiku, sonnet, free verse, limerick.
---

# Poem Generator Skill

## Purpose
Write poems in any style: haiku, sonnet, free verse, limerick.

## When to Activate
Activate when the user asks to:
- write a poem
- poetry about
- haiku
- sonnet

## Core Workflows

Prompt: `Write a {style} poem about {topic} that evokes {emotion}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
