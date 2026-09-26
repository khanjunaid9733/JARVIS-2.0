---
name: netadmin-monitor-uptime
description: Monitor service uptime and alert on downtime.
---

# Uptime Monitor Skill

## Purpose
Monitor service uptime and alert on downtime.

## When to Activate
Activate when the user asks to:
- uptime monitor
- service down alert
- check service
- is server up

## Core Workflows

Poll HTTP endpoint every minute, compare status, alert via Telegram/Slack on failure.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
