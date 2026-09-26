---
name: si-public-speak
description: Provide frameworks and practice for public speaking.
---

# Public Speaking Coach Skill

## Purpose
Provide frameworks and practice for public speaking.

## When to Activate
Activate when the user asks to:
- public speaking
- presentation skills
- overcome stage fright
- speech tips

## Core Workflows

Prompt: `Coach me on {speaking_challenge}. Provide: framework, technique, practice exercise, mindset tip.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
