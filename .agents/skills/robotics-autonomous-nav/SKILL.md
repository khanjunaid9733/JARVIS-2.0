---
name: robotics-autonomous-nav
description: Navigate a robot to a GPS or grid coordinate autonomously.
---

# Autonomous Navigation Skill

## Purpose
Navigate a robot to a GPS or grid coordinate autonomously.

## When to Activate
Activate when the user asks to:
- navigate to
- go to coordinates
- autonomous movement
- robot navigation

## Core Workflows

Plan path with A* on map → translate to motor commands → execute with PID.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
