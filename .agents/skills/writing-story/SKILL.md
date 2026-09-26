---
name: writing-story
description: Write original short stories, flash fiction, and creative narratives.
---

# Creative Story Writer Skill

## Purpose
Write original short stories, flash fiction, and creative narratives.

## When to Activate
Activate when the user asks to:
- write a story
- short story
- fiction about
- creative writing

## Core Workflows

Prompt: `Write a {genre} story about {premise} with a compelling character arc and unexpected ending.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
