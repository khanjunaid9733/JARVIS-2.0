---
name: health-water-track
description: Track daily water intake and send reminders.
---

# Hydration Tracker Skill

## Purpose
Track daily water intake and send reminders.

## When to Activate
Activate when the user asks to:
- log water
- track hydration
- water reminder
- how much water drank

## Core Workflows

Store daily intake in JARVIS_HOME/health/water.csv. Alert every 2 hours.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
