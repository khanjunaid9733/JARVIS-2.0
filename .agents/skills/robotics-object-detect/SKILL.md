---
name: robotics-object-detect
description: Detect and classify objects in camera frames using YOLO.
---

# Object Detection Skill

## Purpose
Detect and classify objects in camera frames using YOLO.

## When to Activate
Activate when the user asks to:
- detect objects
- object detection
- what is in view
- find objects

## Core Workflows

```python
from ultralytics import YOLO; model = YOLO('yolov8n.pt'); results = model(frame)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
