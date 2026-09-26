---
name: writing-expand
description: Expand short bullet points or outlines into full-length content.
---

# Content Expander Skill

## Purpose
Expand short bullet points or outlines into full-length content.

## When to Activate
Activate when the user asks to:
- expand this
- write more about
- flesh out
- make longer

## Core Workflows

Prompt: `Expand the following into a detailed {word_count}-word piece: {outline}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
