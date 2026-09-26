---
name: comm-chat-log
description: Export and archive conversation logs from Slack or Teams.
---

# Chat Log Exporter Skill

## Purpose
Export and archive conversation logs from Slack or Teams.

## When to Activate
Activate when the user asks to:
- export chat log
- save Slack history
- archive messages

## Core Workflows

Use Slack API `conversations.history` endpoint to fetch and save messages.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
