---
name: comm-broadcast-alert
description: Send alerts simultaneously across Slack, Telegram, Email, and Discord.
---

# Multi-Channel Broadcast Skill

## Purpose
Send alerts simultaneously across Slack, Telegram, Email, and Discord.

## When to Activate
Activate when the user asks to:
- broadcast alert
- send everywhere
- multi-channel message

## Core Workflows

Call all communication adapters in parallel with the same message payload.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
