---
name: robotics-battery-monitor
description: Monitor robot battery voltage and warn on low charge.
---

# Battery Monitor Skill

## Purpose
Monitor robot battery voltage and warn on low charge.

## When to Activate
Activate when the user asks to:
- battery voltage
- charge level
- low battery
- battery monitor

## Core Workflows

Read ADC voltage divider output, calculate percentage, alert below threshold.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
