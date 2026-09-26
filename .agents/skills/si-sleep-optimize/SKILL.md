---
name: si-sleep-optimize
description: Optimize sleep quality with science-based recommendations.
---

# Sleep Optimization Guide Skill

## Purpose
Optimize sleep quality with science-based recommendations.

## When to Activate
Activate when the user asks to:
- better sleep
- sleep tips
- insomnia
- sleep hygiene

## Core Workflows

Prompt: `Create a sleep optimization plan. Cover: environment, schedule, pre-sleep routine, nutrition, exercise timing.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
