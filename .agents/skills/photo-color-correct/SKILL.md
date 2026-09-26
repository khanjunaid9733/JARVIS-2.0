---
name: photo-color-correct
description: Apply color correction, contrast, and saturation adjustments.
---

# Color Correction Skill

## Purpose
Apply color correction, contrast, and saturation adjustments.

## When to Activate
Activate when the user asks to:
- color correct
- enhance photo
- adjust brightness
- increase contrast

## Core Workflows

```python
from PIL import ImageEnhance; ImageEnhance.Contrast(img).enhance(1.3)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
