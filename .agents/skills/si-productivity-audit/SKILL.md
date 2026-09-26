---
name: si-productivity-audit
description: Analyze and improve current work habits and time usage.
---

# Productivity Audit Skill

## Purpose
Analyze and improve current work habits and time usage.

## When to Activate
Activate when the user asks to:
- productivity audit
- time management
- work habits
- improve productivity

## Core Workflows

Prompt: `Audit these work habits: {habits}. Identify top 3 improvements and create an action plan.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
