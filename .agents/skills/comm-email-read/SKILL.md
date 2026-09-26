---
name: comm-email-read
description: Fetch and parse emails from Gmail or IMAP accounts.
---

# Read Email Skill

## Purpose
Fetch and parse emails from Gmail or IMAP accounts.

## When to Activate
Activate when the user asks to:
- check email
- read inbox
- latest emails
- unread messages

## Core Workflows

Use `imaplib` to connect to IMAP server, fetch UNSEEN emails, decode MIME parts.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
