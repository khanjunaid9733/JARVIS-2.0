---
name: smarthome-vacuum
description: Start, stop, dock, and schedule robot vacuum cleaning.
---

# Robot Vacuum Control Skill

## Purpose
Start, stop, dock, and schedule robot vacuum cleaning.

## When to Activate
Activate when the user asks to:
- start vacuum
- dock robot
- clean room
- schedule vacuuming

## Core Workflows

Use Roborock or iRobot API, or route via Home Assistant vacuum services.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
