---
name: health-stress-manage
description: Provide evidence-based stress management techniques.
---

# Stress Management Guide Skill

## Purpose
Provide evidence-based stress management techniques.

## When to Activate
Activate when the user asks to:
- I'm stressed
- stress management
- calm down
- anxiety relief

## Core Workflows

Offer: 4-7-8 breathing, progressive muscle relaxation, cognitive reframing steps.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
