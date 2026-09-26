---
name: photo-watermark
description: Add text or image watermarks to photos.
---

# Watermark Adder Skill

## Purpose
Add text or image watermarks to photos.

## When to Activate
Activate when the user asks to:
- add watermark
- watermark photo
- brand images
- copyright mark

## Core Workflows

```python
from PIL import ImageDraw; draw.text((x,y), text, fill=(255,255,255,128))
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
