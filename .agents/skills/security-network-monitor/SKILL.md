---
name: security-network-monitor
description: Monitor for suspicious network connections and alert.
---

# Network Intrusion Monitor Skill

## Purpose
Monitor for suspicious network connections and alert.

## When to Activate
Activate when the user asks to:
- network intrusion
- suspicious connections
- monitor traffic

## Core Workflows

Use `psutil.net_connections()` + whitelist filter to detect unexpected external connections.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
