---
name: comm-whatsapp
description: Send WhatsApp messages via Twilio or WhatsApp Business API.
---

# WhatsApp Sender Skill

## Purpose
Send WhatsApp messages via Twilio or WhatsApp Business API.

## When to Activate
Activate when the user asks to:
- send WhatsApp message
- WhatsApp <contact>

## Core Workflows

Use Twilio API: POST to `messaging/v1/Messages` with WhatsApp `To:` prefix.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
