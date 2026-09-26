---
name: security-certificate-gen
description: Generate TLS certificates for local dev or internal services.
---

# Self-Signed Certificate Generator Skill

## Purpose
Generate TLS certificates for local dev or internal services.

## When to Activate
Activate when the user asks to:
- generate certificate
- create TLS cert
- self-signed cert

## Core Workflows

```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
