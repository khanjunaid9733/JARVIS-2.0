---
name: gaming-dnd-dm
description: Act as a text-based D&D Dungeon Master for interactive adventures.
---

# D&D Dungeon Master Skill

## Purpose
Act as a text-based D&D Dungeon Master for interactive adventures.

## When to Activate
Activate when the user asks to:
- play D&D
- dungeon master
- D&D adventure
- tabletop RPG

## Core Workflows

Prompt: `Act as a D&D Dungeon Master for a {setting} adventure. Start the session and narrate in second person.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
