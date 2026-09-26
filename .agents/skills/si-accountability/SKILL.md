---
name: si-accountability
description: Check in on goal progress and provide accountability coaching.
---

# Accountability Partner Skill

## Purpose
Check in on goal progress and provide accountability coaching.

## When to Activate
Activate when the user asks to:
- accountability
- check in on goals
- am I on track
- hold me accountable

## Core Workflows

Prompt: `Act as an accountability coach. Review: {goals_and_progress}. Celebrate wins, address blocks, next steps.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
