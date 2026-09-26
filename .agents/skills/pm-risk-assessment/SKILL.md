---
name: pm-risk-assessment
description: Identify project risks and create a probability-impact matrix.
---

# Risk Assessment Matrix Skill

## Purpose
Identify project risks and create a probability-impact matrix.

## When to Activate
Activate when the user asks to:
- risk assessment
- identify risks
- project risks
- risk matrix

## Core Workflows

Prompt: `Identify 10 risks for {project}. Rate each by probability (1-5) and impact (1-5). Suggest mitigations.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
