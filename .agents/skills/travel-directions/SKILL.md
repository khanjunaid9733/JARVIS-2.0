---
name: travel-directions
description: Get turn-by-turn directions between locations.
---

# Directions & Route Planner Skill

## Purpose
Get turn-by-turn directions between locations.

## When to Activate
Activate when the user asks to:
- directions to
- route from to
- how to get to
- navigate

## Core Workflows

Use Google Maps Directions API or OpenRouteService API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
