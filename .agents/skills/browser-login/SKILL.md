---
name: browser-login
description: Automate login to websites with stored credentials.
---

# Website Login Automator Skill

## Purpose
Automate login to websites with stored credentials.

## When to Activate
Activate when the user asks to:
- log in to <site>
- automate login
- sign in to <site>

## Core Workflows

Fill username/password fields, click submit, wait for authentication confirmation.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
