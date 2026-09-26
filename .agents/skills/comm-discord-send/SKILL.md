---
name: comm-discord-send
description: Post messages to Discord channels via webhooks or bot.
---

# Discord Message Sender Skill

## Purpose
Post messages to Discord channels via webhooks or bot.

## When to Activate
Activate when the user asks to:
- send Discord message
- post to Discord
- Discord alert

## Core Workflows

POST to Discord webhook URL with `{content: message}`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
