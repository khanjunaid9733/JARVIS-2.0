---
name: ai-code-explain
description: Explain what any piece of code does in plain language.
---

# AI Code Explainer Skill

## Purpose
Explain what any piece of code does in plain language.

## When to Activate
Activate when the user asks to:
- explain this code
- what does this do
- walk me through code

## Core Workflows

Prompt: `Explain step-by-step what the following code does: {code}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
