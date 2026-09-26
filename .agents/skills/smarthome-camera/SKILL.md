---
name: smarthome-camera
description: Fetch snapshots or streams from IP cameras.
---

# Security Camera View Skill

## Purpose
Fetch snapshots or streams from IP cameras.

## When to Activate
Activate when the user asks to:
- show camera
- what's on camera
- security feed

## Core Workflows

GET snapshot URL from camera API or RTSP stream via ffmpeg.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
