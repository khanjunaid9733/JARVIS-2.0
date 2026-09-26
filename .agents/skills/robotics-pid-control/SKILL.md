---
name: robotics-pid-control
description: Implement PID feedback control loops for motors and sensors.
---

# PID Controller Skill

## Purpose
Implement PID feedback control loops for motors and sensors.

## When to Activate
Activate when the user asks to:
- PID controller
- motor control loop
- error correction
- feedback control

## Core Workflows

Update = Kp×error + Ki×∫error + Kd×(d_error/dt). Tune gains empirically.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
