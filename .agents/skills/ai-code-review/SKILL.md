---
name: ai-code-review
description: Review code for quality, security, and best practices.
---

# AI Code Reviewer Skill

## Purpose
Review code for quality, security, and best practices.

## When to Activate
Activate when the user asks to:
- review this code
- code review
- check code quality

## Core Workflows

Prompt: `Review the following code for quality, security flaws, and best practice violations: {code}`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
