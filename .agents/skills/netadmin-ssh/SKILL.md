---
name: netadmin-ssh
description: Execute commands on remote servers via SSH.
---

# SSH Command Runner Skill

## Purpose
Execute commands on remote servers via SSH.

## When to Activate
Activate when the user asks to:
- SSH into
- run command on server
- remote command
- connect to server

## Core Workflows

```python
import paramiko; client.connect(host, username=user, password=pwd); client.exec_command(cmd)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
