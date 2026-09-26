---
name: web-download-file
description: Download any file from a URL to local disk with progress tracking.
---

# Download File Skill

## Purpose
Download any file from a URL to local disk with progress tracking.

## When to Activate
Activate when the user asks to:
- download <url>
- save file from <url>

## Core Workflows

```python
urllib.request.urlretrieve(url, filename)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
