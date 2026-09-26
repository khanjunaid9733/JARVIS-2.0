---
name: netadmin-log-rotate
description: Configure logrotate for application log management.
---

# Log Rotation Setup Skill

## Purpose
Configure logrotate for application log management.

## When to Activate
Activate when the user asks to:
- log rotation
- logrotate
- rotate logs
- log management

## Core Workflows

Generate `/etc/logrotate.d/app` config with size, frequency, and compression.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
