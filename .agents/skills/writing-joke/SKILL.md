---
name: writing-joke
description: Write jokes, puns, one-liners, and humorous content.
---

# Joke & Humor Writer Skill

## Purpose
Write jokes, puns, one-liners, and humorous content.

## When to Activate
Activate when the user asks to:
- tell me a joke
- funny pun
- write jokes about
- humor

## Core Workflows

Prompt: `Write 5 clever, clean jokes about {topic}. Mix puns, one-liners, and observational humor.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
