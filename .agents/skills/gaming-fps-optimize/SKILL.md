---
name: gaming-fps-optimize
description: Suggest in-game and system settings to improve FPS performance.
---

# FPS Optimizer Skill

## Purpose
Suggest in-game and system settings to improve FPS performance.

## When to Activate
Activate when the user asks to:
- increase FPS
- improve performance
- low FPS
- game stuttering

## Core Workflows

Prompt: `Provide settings optimizations for {game} on {hardware} to maximize FPS. Include in-game and Windows settings.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
