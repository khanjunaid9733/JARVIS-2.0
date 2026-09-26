---
name: productivity-email-triage
description: Classify, prioritize, and draft responses to emails.
---

# Email Triage Assistant Skill

## Purpose
Classify, prioritize, and draft responses to emails.

## When to Activate
Activate when the user asks to:
- triage email
- prioritize inbox
- email responses
- email assistant

## Core Workflows

Fetch inbox via IMAP, classify by urgency/topic, draft LLM responses.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
