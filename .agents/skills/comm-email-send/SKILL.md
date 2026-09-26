---
name: comm-email-send
description: Send emails via SMTP with attachments and HTML body.
---

# Send Email Skill

## Purpose
Send emails via SMTP with attachments and HTML body.

## When to Activate
Activate when the user asks to:
- send email to
- email <person>
- send message via email

## Core Workflows

```python
import smtplib; smtplib.SMTP_SSL('smtp.gmail.com', 465).sendmail(...)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
