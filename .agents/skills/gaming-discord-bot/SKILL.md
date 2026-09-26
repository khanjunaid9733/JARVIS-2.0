---
name: gaming-discord-bot
description: Trigger Discord bot actions via API for gaming communities.
---

# Discord Bot Command Skill

## Purpose
Trigger Discord bot actions via API for gaming communities.

## When to Activate
Activate when the user asks to:
- Discord bot
- bot command
- Discord server action

## Core Workflows

POST to Discord REST API with bot token and application commands.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
