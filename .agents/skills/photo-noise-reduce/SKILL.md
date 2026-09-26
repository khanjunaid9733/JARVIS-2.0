---
name: photo-noise-reduce
description: Apply denoising filters to reduce grain in photos.
---

# Image Noise Reducer Skill

## Purpose
Apply denoising filters to reduce grain in photos.

## When to Activate
Activate when the user asks to:
- remove noise
- denoise photo
- reduce grain
- sharpen image

## Core Workflows

```python
cv2.fastNlMeansDenoisingColored(img, h=10, hColor=10, templateWindowSize=7, searchWindowSize=21)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
