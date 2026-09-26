---
name: files-hash
description: Compute MD5, SHA256, or SHA512 hash of any file.
---

# File Hash / Checksum Skill

## Purpose
Compute MD5, SHA256, or SHA512 hash of any file.

## When to Activate
Activate when the user asks to:
- hash <file>
- checksum <file>
- sha256 of <file>

## Core Workflows

```python
import hashlib; hashlib.sha256(open(path,'rb').read()).hexdigest()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
