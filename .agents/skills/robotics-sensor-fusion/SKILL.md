---
name: robotics-sensor-fusion
description: Fuse data from multiple sensors using Kalman filtering.
---

# Sensor Fusion Skill

## Purpose
Fuse data from multiple sensors using Kalman filtering.

## When to Activate
Activate when the user asks to:
- sensor fusion
- Kalman filter
- combine sensors
- IMU fusion

## Core Workflows

Apply Extended Kalman Filter to fuse IMU + GPS + encoder odometry.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
