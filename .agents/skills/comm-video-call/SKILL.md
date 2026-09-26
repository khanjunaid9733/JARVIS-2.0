---
name: comm-video-call
description: Launch or schedule a Zoom, Teams, or Google Meet call.
---

# Video Call Initiator Skill

## Purpose
Launch or schedule a Zoom, Teams, or Google Meet call.

## When to Activate
Activate when the user asks to:
- start Zoom call
- create Meet link
- schedule video call

## Core Workflows

Generate a Google Meet link via Google Calendar API or open Zoom URI.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
