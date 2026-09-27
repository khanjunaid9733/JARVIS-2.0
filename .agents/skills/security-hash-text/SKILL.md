---
name: security-hash-text
description: Compute the SHA-256 checksum digest of a text string.
---

# Text Digest Skill

## Purpose
Compute the SHA-256 checksum digest of a text string.

## When to Activate
Activate when the user asks to:
- hash a text string
- checksum a string
- sha256 of text
- digest a string

## Core Workflows

The digest is the workflow's RESULT, so the snippet prints it: the caller binds
the text as the Python variable `text` and reads exactly one sha256 hex digest
from stdout. A workflow that computes a digest and discards it cannot be
adjudicated by anybody.

```python
import hashlib; print(hashlib.sha256(text.encode('utf-8')).hexdigest())
```

## Parameters

- `text` (string, required): the text to digest; the dispatch context binds it as the Python variable `text`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Emit exactly one sha256 hex digest on stdout so the caller can adjudicate it.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
