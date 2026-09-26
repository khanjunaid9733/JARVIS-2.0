---
name: media-image-resize
description: Resize, crop, rotate, and reformat images.
---

# Image Resizer Skill

## Purpose
Resize, crop, rotate, and reformat images.

## When to Activate
Activate when the user asks to:
- resize image
- crop <image>
- scale image to

## Core Workflows

```python
from PIL import Image; Image.open(path).resize((w,h)).save(out)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
