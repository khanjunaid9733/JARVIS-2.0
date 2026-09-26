---
name: netadmin-network-scan
description: Discover all devices on a local network.
---

# Network Discovery Scanner Skill

## Purpose
Discover all devices on a local network.

## When to Activate
Activate when the user asks to:
- network scan
- discover devices
- what's on my network
- nmap

## Core Workflows

```bash
nmap -sn 192.168.1.0/24  # or use Python socket-based scanner
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
