---
name: language-formal-informal
description: Rewrite text in formal, informal, or professional register.
---

# Register Converter Skill

## Purpose
Rewrite text in formal, informal, or professional register.

## When to Activate
Activate when the user asks to:
- make formal
- make casual
- professional tone
- rewrite more formally

## Core Workflows

Prompt: `Rewrite the following in {register} register: {text}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
