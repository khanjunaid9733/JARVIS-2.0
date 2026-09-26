---
name: netadmin-package-update
description: Update system packages on Linux or Windows Server.
---

# Package Update Manager Skill

## Purpose
Update system packages on Linux or Windows Server.

## When to Activate
Activate when the user asks to:
- update packages
- apt update
- yum update
- system update

## Core Workflows

```bash
apt update && apt upgrade -y  # or yum update -y
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
