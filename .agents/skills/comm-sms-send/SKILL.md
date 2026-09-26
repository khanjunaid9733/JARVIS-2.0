---
name: comm-sms-send
description: Send SMS text messages via Twilio or Vonage.
---

# SMS Sender Skill

## Purpose
Send SMS text messages via Twilio or Vonage.

## When to Activate
Activate when the user asks to:
- send SMS
- text <phone number>
- send text to

## Core Workflows

POST to Twilio API `/2010-04-01/Accounts/<SID>/Messages.json` with From/To/Body.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
