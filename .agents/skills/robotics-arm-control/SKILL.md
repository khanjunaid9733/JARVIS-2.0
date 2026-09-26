---
name: robotics-arm-control
description: Control servo angles for a multi-DOF robotic arm.
---

# Robotic Arm Controller Skill

## Purpose
Control servo angles for a multi-DOF robotic arm.

## When to Activate
Activate when the user asks to:
- robot arm
- servo angles
- arm pose
- pick and place

## Core Workflows

Compute inverse kinematics (geometric or DH parameters), map to servo PWM.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
