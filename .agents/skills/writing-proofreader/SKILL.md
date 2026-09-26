---
name: writing-proofreader
description: Proofread text for grammar, spelling, style, and clarity.
---

# Grammar & Style Checker Skill

## Purpose
Proofread text for grammar, spelling, style, and clarity.

## When to Activate
Activate when the user asks to:
- proofread
- grammar check
- fix my writing
- check spelling

## Core Workflows

Prompt: `Proofread and fix all grammar, spelling, and style issues in: {text}. Return corrected version.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
