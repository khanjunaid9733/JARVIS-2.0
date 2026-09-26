---
name: marketing-roi-calc
description: Calculate ROI for campaigns from cost and revenue data.
---

# Marketing ROI Calculator Skill

## Purpose
Calculate ROI for campaigns from cost and revenue data.

## When to Activate
Activate when the user asks to:
- marketing ROI
- campaign ROI
- return on investment
- ad spend ROI

## Core Workflows

ROI = (Revenue - Cost) / Cost × 100. Include ROAS, CPA, and CPL metrics.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
