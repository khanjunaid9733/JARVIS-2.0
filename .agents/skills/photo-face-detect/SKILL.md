---
name: photo-face-detect
description: Detect and count faces in images using OpenCV or face_recognition.
---

# Face Detector Skill

## Purpose
Detect and count faces in images using OpenCV or face_recognition.

## When to Activate
Activate when the user asks to:
- detect faces
- find faces
- face count
- face recognition

## Core Workflows

```python
import face_recognition; face_recognition.face_locations(img_array)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
