---
name: netadmin-systemd-service
description: Create, enable, start, and monitor systemd services.
---

# systemd Service Manager Skill

## Purpose
Create, enable, start, and monitor systemd services.

## When to Activate
Activate when the user asks to:
- systemd service
- service file
- enable service
- start daemon

## Core Workflows

Generate unit file, run `systemctl daemon-reload && systemctl enable --now <name>.service`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
