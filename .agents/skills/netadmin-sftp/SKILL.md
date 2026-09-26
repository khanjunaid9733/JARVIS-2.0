---
name: netadmin-sftp
description: Transfer files to/from remote servers via SFTP.
---

# SFTP File Transfer Skill

## Purpose
Transfer files to/from remote servers via SFTP.

## When to Activate
Activate when the user asks to:
- SFTP upload
- SFTP download
- transfer to server
- remote file copy

## Core Workflows

```python
client.open_sftp().put(local_path, remote_path)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
