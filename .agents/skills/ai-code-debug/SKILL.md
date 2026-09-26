---
name: ai-code-debug
description: Identify and fix bugs in any code snippet.
---

# AI Code Debugger Skill

## Purpose
Identify and fix bugs in any code snippet.

## When to Activate
Activate when the user asks to:
- debug this
- fix this code
- find the bug
- why is this failing

## Core Workflows

Prompt: `Find and fix bugs in: {code}. Explain each fix.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
