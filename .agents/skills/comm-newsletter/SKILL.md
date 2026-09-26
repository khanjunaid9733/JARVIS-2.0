---
name: comm-newsletter
description: Draft and send bulk newsletters via Mailchimp or Sendgrid.
---

# Newsletter Composer Skill

## Purpose
Draft and send bulk newsletters via Mailchimp or Sendgrid.

## When to Activate
Activate when the user asks to:
- send newsletter
- bulk email
- email campaign

## Core Workflows

Use SendGrid API: POST `/mail/send` with recipient list and template ID.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
