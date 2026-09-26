---
name: comm-telegram-send
description: Send Telegram messages, photos, and files via Bot API.
---

# Telegram Message Sender Skill

## Purpose
Send Telegram messages, photos, and files via Bot API.

## When to Activate
Activate when the user asks to:
- send Telegram message
- Telegram me
- notify via Telegram

## Core Workflows

GET `https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<ID>&text=<MSG>`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
