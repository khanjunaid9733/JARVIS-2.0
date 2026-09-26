---
name: security-ssl-check
description: Check SSL certificate validity, expiry, and chain for any domain.
---

# SSL Certificate Inspector Skill

## Purpose
Check SSL certificate validity, expiry, and chain for any domain.

## When to Activate
Activate when the user asks to:
- check SSL
- certificate expiry
- is <domain> secure
- TLS check

## Core Workflows

```python
import ssl, socket; ssl.get_server_certificate(('<host>', 443))
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
