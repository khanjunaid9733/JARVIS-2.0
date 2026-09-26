---
name: photo-background-remove
description: Remove backgrounds from product and portrait images.
---

# Background Remover Skill

## Purpose
Remove backgrounds from product and portrait images.

## When to Activate
Activate when the user asks to:
- remove background
- transparent background
- cut out image

## Core Workflows

```python
from rembg import remove; output = remove(open(path, 'rb').read())
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
