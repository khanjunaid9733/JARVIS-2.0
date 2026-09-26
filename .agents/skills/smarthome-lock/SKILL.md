---
name: smarthome-lock
description: Lock or unlock smart door locks via Home Assistant or August API.
---

# Smart Lock Control Skill

## Purpose
Lock or unlock smart door locks via Home Assistant or August API.

## When to Activate
Activate when the user asks to:
- lock door
- unlock front door
- is door locked

## Core Workflows

POST to Home Assistant `lock.lock` / `lock.unlock` service.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
