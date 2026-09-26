---
name: health-step-count
description: Sync and display step count data from fitness APIs.
---

# Step Counter Integrator Skill

## Purpose
Sync and display step count data from fitness APIs.

## When to Activate
Activate when the user asks to:
- steps today
- step count
- how many steps
- fitness tracker

## Core Workflows

Query Google Fit, Apple Health, or Fitbit API for daily step data.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
