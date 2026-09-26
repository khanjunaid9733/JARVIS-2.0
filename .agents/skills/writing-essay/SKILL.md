---
name: writing-essay
description: Write full essays on any topic with structured arguments.
---

# Essay Writer Skill

## Purpose
Write full essays on any topic with structured arguments.

## When to Activate
Activate when the user asks to:
- write essay
- essay about
- academic essay
- argumentative essay

## Core Workflows

Prompt: `Write a {word_count}-word {type} essay on: {topic}. Include introduction, body paragraphs, and conclusion.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
