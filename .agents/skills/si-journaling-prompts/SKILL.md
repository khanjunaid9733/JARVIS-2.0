---
name: si-journaling-prompts
description: Generate deep self-reflection journaling prompts.
---

# Journal Prompts Skill

## Purpose
Generate deep self-reflection journaling prompts.

## When to Activate
Activate when the user asks to:
- journaling prompts
- reflection questions
- self-discovery
- journal about

## Core Workflows

Prompt: `Generate 10 deep self-reflection prompts for someone exploring {topic/life_area}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
