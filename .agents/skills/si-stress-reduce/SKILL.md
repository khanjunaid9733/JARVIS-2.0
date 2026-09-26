---
name: si-stress-reduce
description: Develop a personalized stress management strategy.
---

# Stress Reduction Plan Skill

## Purpose
Develop a personalized stress management strategy.

## When to Activate
Activate when the user asks to:
- reduce stress
- stress management
- anxiety relief
- calm down

## Core Workflows

Prompt: `Create a stress reduction plan for {stressor/lifestyle}. Include: immediate techniques, long-term strategies, lifestyle changes.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
