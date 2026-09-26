---
name: robotics-camera-capture
description: Capture frames from connected cameras using OpenCV.
---

# Robot Camera Capture Skill

## Purpose
Capture frames from connected cameras using OpenCV.

## When to Activate
Activate when the user asks to:
- camera capture
- robot vision
- webcam frame
- take photo

## Core Workflows

```python
import cv2; cap = cv2.VideoCapture(0); ret, frame = cap.read()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
