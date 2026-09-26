---
name: marketing-content-strategy
description: Build a complete content marketing strategy.
---

# Content Strategy Planner Skill

## Purpose
Build a complete content marketing strategy.

## When to Activate
Activate when the user asks to:
- content strategy
- marketing plan
- editorial calendar
- content plan

## Core Workflows

Prompt: `Create a 3-month content marketing strategy for {brand} targeting {audience}. Include formats, channels, topics.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
