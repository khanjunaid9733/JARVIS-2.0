---
name: social-viral-hook
description: Generate attention-grabbing opening lines for posts.
---

# Viral Hook Generator Skill

## Purpose
Generate attention-grabbing opening lines for posts.

## When to Activate
Activate when the user asks to:
- write hook
- attention grabbing opener
- viral headline

## Core Workflows

Prompt: `Write 10 viral hooks for a {topic} post that will stop the scroll.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
