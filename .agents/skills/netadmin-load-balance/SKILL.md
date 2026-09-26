---
name: netadmin-load-balance
description: Generate load balancer configurations for nginx or HAProxy.
---

# Load Balancer Config Skill

## Purpose
Generate load balancer configurations for nginx or HAProxy.

## When to Activate
Activate when the user asks to:
- load balancer
- upstream servers
- round robin
- HA proxy config

## Core Workflows

Generate nginx upstream block or HAProxy backend config with health checks.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
