---
name: gaming-cheats
description: Find walkthroughs, tips, and cheat codes for any game.
---

# Game Guide & Cheats Skill

## Purpose
Find walkthroughs, tips, and cheat codes for any game.

## When to Activate
Activate when the user asks to:
- cheats for
- game guide
- how to beat
- walkthrough
- tips for

## Core Workflows

Prompt: `Provide tips, strategies, and common techniques for {game}. Focus on {aspect}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
