---
name: social-content-calendar
description: Create a 30-day social media content plan.
---

# Content Calendar Builder Skill

## Purpose
Create a 30-day social media content plan.

## When to Activate
Activate when the user asks to:
- content calendar
- social media plan
- 30 day posting schedule

## Core Workflows

Prompt LLM: `Create a 30-day content calendar for {brand/topic} across Facebook, Instagram, Twitter.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
