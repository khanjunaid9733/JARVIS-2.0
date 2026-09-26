---
name: smarthome-ota-update
description: Trigger OTA firmware updates for smart home devices.
---

# Smart Device Firmware Update Skill

## Purpose
Trigger OTA firmware updates for smart home devices.

## When to Activate
Activate when the user asks to:
- update smart devices
- firmware update
- ota update

## Core Workflows

Use Home Assistant `update.install` service for supported devices.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
