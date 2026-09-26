---
name: desktop-clipboard
description: Read from or write text/images to the Windows clipboard.
---

# Clipboard Manager Skill

## Purpose
Read from or write text/images to the Windows clipboard.

## When to Activate
Activate when the user asks to:
- copy to clipboard
- read clipboard
- paste <text>
- clear clipboard

## Core Workflows

```python
import subprocess; subprocess.run(['clip'], input=text.encode())
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
