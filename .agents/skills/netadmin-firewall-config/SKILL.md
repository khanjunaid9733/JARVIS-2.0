---
name: netadmin-firewall-config
description: Configure ufw or iptables firewall rules on Linux.
---

# Linux Firewall (ufw/iptables) Skill

## Purpose
Configure ufw or iptables firewall rules on Linux.

## When to Activate
Activate when the user asks to:
- firewall rules
- ufw allow
- iptables
- block port Linux

## Core Workflows

```bash
ufw allow 443/tcp; ufw deny 22; ufw enable
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
