---
name: files-image-view
description: View images, get dimensions, format, and EXIF metadata.
---

# Image Viewer & Info Skill

## Purpose
View images, get dimensions, format, and EXIF metadata.

## When to Activate
Activate when the user asks to:
- show image
- image info
- what size is <image>

## Core Workflows

```python
from PIL import Image; img = Image.open(path); print(img.size, img.format)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
