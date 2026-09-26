---
name: ai-persona
description: Activate a custom AI persona with specific personality traits and expertise.
---

# AI Persona Mode Skill

## Purpose
Activate a custom AI persona with specific personality traits and expertise.

## When to Activate
Activate when the user asks to:
- act as <persona>
- you are now
- role play as
- speak as

## Core Workflows

Prepend system prompt: `You are {persona} with expertise in {domain}. Respond in character.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
