---
name: gaming-create-character
description: Create detailed RPG characters with backstory and stat allocation.
---

# RPG Character Creator Skill

## Purpose
Create detailed RPG characters with backstory and stat allocation.

## When to Activate
Activate when the user asks to:
- create character
- RPG character
- character backstory
- character sheet

## Core Workflows

Prompt: `Create a detailed {class} character for {game/setting}. Include: stats, backstory, traits, goals.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
