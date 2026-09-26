---
name: writing-script
description: Write scripts for YouTube videos, podcasts, or presentations.
---

# Script Writer Skill

## Purpose
Write scripts for YouTube videos, podcasts, or presentations.

## When to Activate
Activate when the user asks to:
- write script
- YouTube script
- podcast script
- presentation script

## Core Workflows

Prompt: `Write a {duration}-minute {format} script about {topic} with engaging transitions.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
