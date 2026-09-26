---
name: comm-slack-message
description: Send messages to any Slack channel or user via webhook or API.
---

# Slack Message Sender Skill

## Purpose
Send messages to any Slack channel or user via webhook or API.

## When to Activate
Activate when the user asks to:
- send Slack message
- post to Slack
- Slack <channel>

## Core Workflows

POST to `https://hooks.slack.com/services/XXX/YYY/ZZZ` with `{text: message}`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
