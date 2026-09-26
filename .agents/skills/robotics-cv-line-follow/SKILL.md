---
name: robotics-cv-line-follow
description: Implement computer vision line following for autonomous robots.
---

# Line Following Robot Skill

## Purpose
Implement computer vision line following for autonomous robots.

## When to Activate
Activate when the user asks to:
- line follower
- follow line
- track path
- CV navigation

## Core Workflows

Detect line centroid in camera frame, compute error, apply PID to steering.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
