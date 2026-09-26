---
name: netadmin-smtp-test
description: Test SMTP server connectivity and email delivery.
---

# SMTP Mail Server Tester Skill

## Purpose
Test SMTP server connectivity and email delivery.

## When to Activate
Activate when the user asks to:
- test SMTP
- email server test
- mail delivery
- SMTP check

## Core Workflows

```python
import smtplib; smtplib.SMTP('host', port).ehlo()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
