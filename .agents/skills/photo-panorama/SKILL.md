---
name: photo-panorama
description: Stitch multiple overlapping images into a panorama.
---

# Panorama Stitcher Skill

## Purpose
Stitch multiple overlapping images into a panorama.

## When to Activate
Activate when the user asks to:
- panorama
- stitch images
- wide photo
- 360 view

## Core Workflows

```python
import cv2; stitcher = cv2.Stitcher.create(); stitcher.stitch(images)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
