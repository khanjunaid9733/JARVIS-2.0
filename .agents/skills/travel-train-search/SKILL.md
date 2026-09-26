---
name: travel-train-search
description: Search train routes and schedules between cities.
---

# Train & Rail Search Skill

## Purpose
Search train routes and schedules between cities.

## When to Activate
Activate when the user asks to:
- train from to
- rail route
- train schedule
- Amtrak
- Eurostar

## Core Workflows

Use Rome2Rio API or national rail APIs for route and schedule data.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
