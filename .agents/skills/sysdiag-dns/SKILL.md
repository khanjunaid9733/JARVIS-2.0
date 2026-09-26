---
name: sysdiag-dns
description: Resolve domain names and query DNS records.
---

# DNS Lookup Skill

## Purpose
Resolve domain names and query DNS records.

## When to Activate
Activate when the user asks to:
- DNS lookup
- resolve <domain>
- MX record for

## Core Workflows

```python
import socket; socket.getaddrinfo('<domain>', None)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
