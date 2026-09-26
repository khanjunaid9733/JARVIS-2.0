---
name: robotics-telemetry
description: Log sensor telemetry with timestamps to a SQLite file.
---

# Robot Telemetry Logger Skill

## Purpose
Log sensor telemetry with timestamps to a SQLite file.

## When to Activate
Activate when the user asks to:
- robot telemetry
- sensor data log
- log robot data

## Core Workflows

Write sensor readings periodically to SQLite with ULID timestamps.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
