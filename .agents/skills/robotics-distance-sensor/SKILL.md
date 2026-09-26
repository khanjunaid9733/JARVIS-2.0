---
name: robotics-distance-sensor
description: Read distance measurements from HC-SR04 ultrasonic sensors.
---

# Ultrasonic Distance Sensor Skill

## Purpose
Read distance measurements from HC-SR04 ultrasonic sensors.

## When to Activate
Activate when the user asks to:
- distance sensor
- ultrasonic
- how far
- proximity sensor

## Core Workflows

Time echo pulse: distance_cm = (pulse_duration × 34300) / 2.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
