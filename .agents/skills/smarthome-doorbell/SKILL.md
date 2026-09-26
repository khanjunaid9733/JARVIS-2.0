---
name: smarthome-doorbell
description: Receive doorbell events and display or relay the camera feed.
---

# Smart Doorbell Skill

## Purpose
Receive doorbell events and display or relay the camera feed.

## When to Activate
Activate when the user asks to:
- someone at the door
- doorbell rang
- show doorbell camera

## Core Workflows

Subscribe to Ring or Nest API webhook, fetch snapshot, send to Telegram.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
