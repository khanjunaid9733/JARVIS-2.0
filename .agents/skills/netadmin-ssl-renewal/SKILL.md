---
name: netadmin-ssl-renewal
description: Check and renew Let's Encrypt SSL certificates.
---

# SSL Certificate Renewal Skill

## Purpose
Check and renew Let's Encrypt SSL certificates.

## When to Activate
Activate when the user asks to:
- renew SSL
- Let's Encrypt
- certbot
- SSL expiry

## Core Workflows

```bash
certbot renew --quiet --post-hook 'systemctl reload nginx'
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
