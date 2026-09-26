---
name: smarthome-notification
description: Send Home Assistant or Google Home notifications to smart displays.
---

# Smart Home Alert Skill

## Purpose
Send Home Assistant or Google Home notifications to smart displays.

## When to Activate
Activate when the user asks to:
- announce on Google Home
- speak on Alexa
- smart display alert

## Core Workflows

POST to `http://<HA_HOST>/api/services/notify/mobile_app_<device>`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
