---
name: photo-compress
description: Compress images to target file size or quality.
---

# Image Compressor Skill

## Purpose
Compress images to target file size or quality.

## When to Activate
Activate when the user asks to:
- compress photo
- reduce image size
- optimize image
- smaller file

## Core Workflows

```python
from PIL import Image; img.save(out, optimize=True, quality=75)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
