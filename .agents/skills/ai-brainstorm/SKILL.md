---
name: ai-brainstorm
description: Generate creative ideas, options, and alternatives for any topic.
---

# AI Brainstormer Skill

## Purpose
Generate creative ideas, options, and alternatives for any topic.

## When to Activate
Activate when the user asks to:
- brainstorm
- give me ideas
- suggest options
- think of ways to

## Core Workflows

Prompt: `Brainstorm 10 creative ideas for: {topic}. Be specific and original.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
