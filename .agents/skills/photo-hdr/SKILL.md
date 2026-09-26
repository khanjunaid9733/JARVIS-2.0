---
name: photo-hdr
description: Create HDR images from exposure-bracketed shots.
---

# HDR Image Creator Skill

## Purpose
Create HDR images from exposure-bracketed shots.

## When to Activate
Activate when the user asks to:
- HDR photo
- high dynamic range
- merge exposures

## Core Workflows

```python
merge = cv2.createMergeDebevec(); hdr = merge.process(images, times=np.array(exposures))
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
