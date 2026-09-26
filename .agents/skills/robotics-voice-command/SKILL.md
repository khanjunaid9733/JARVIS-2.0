---
name: robotics-voice-command
description: Accept voice commands and translate to robot actions.
---

# Voice-Controlled Robot Skill

## Purpose
Accept voice commands and translate to robot actions.

## When to Activate
Activate when the user asks to:
- voice control robot
- talk to robot
- speak command
- voice robot

## Core Workflows

STT → intent classification → action → execute via GPIO or ROS.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
