---
name: si-goal-setting
description: Transform vague goals into specific SMART goals.
---

# SMART Goal Setter Skill

## Purpose
Transform vague goals into specific SMART goals.

## When to Activate
Activate when the user asks to:
- set SMART goal
- goal planning
- goal setting
- specific goal

## Core Workflows

Prompt: `Convert this goal into SMART format: {goal}. Make it Specific, Measurable, Achievable, Relevant, Time-bound.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
