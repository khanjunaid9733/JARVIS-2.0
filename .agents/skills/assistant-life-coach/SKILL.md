---
name: assistant-life-coach
description: Provide goal-setting, accountability, and motivation coaching.
---

# Life Coach Mode Skill

## Purpose
Provide goal-setting, accountability, and motivation coaching.

## When to Activate
Activate when the user asks to:
- life coach
- motivate me
- accountability check
- goal setting

## Core Workflows

Prompt: `Act as a professional life coach. Help me set SMART goals for: {area}. Ask clarifying questions.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
