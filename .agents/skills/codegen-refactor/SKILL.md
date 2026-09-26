---
name: codegen-refactor
description: Refactor existing code for readability, performance, or design patterns.
---

# Code Refactoring Assistant Skill

## Purpose
Refactor existing code for readability, performance, or design patterns.

## When to Activate
Activate when the user asks to:
- refactor this
- improve code
- clean up code
- better code structure

## Core Workflows

Prompt: `Refactor the following code to: {goals}. Explain each change made: {code}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
