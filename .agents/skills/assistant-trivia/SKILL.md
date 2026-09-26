---
name: assistant-trivia
description: Host interactive trivia games on any topic.
---

# Trivia Game Master Skill

## Purpose
Host interactive trivia games on any topic.

## When to Activate
Activate when the user asks to:
- trivia game
- quiz game
- trivia about
- play trivia

## Core Workflows

Generate questions via LLM, track score, provide final results and explanations.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
