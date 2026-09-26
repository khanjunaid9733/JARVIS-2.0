---
name: gaming-trivia
description: Host gaming-themed trivia quizzes.
---

# Gaming Trivia Skill

## Purpose
Host gaming-themed trivia quizzes.

## When to Activate
Activate when the user asks to:
- gaming trivia
- game quiz
- test gaming knowledge

## Core Workflows

Generate 10 gaming trivia questions via LLM across genres, history, and facts.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
