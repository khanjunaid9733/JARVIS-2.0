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

The digest is the workflow's RESULT, so the snippet prints it: a workflow that
computes a hash and discards it leaves its caller nothing to verify, which makes
the skill indistinguishable from one that did nothing.

```python
import hashlib, pathlib; print(hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest())
```

## Parameters

- `path` (string, required): the file to hash; the dispatch context binds it as the Python variable `path`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
