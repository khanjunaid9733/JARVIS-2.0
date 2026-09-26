---
name: photo-histogram
description: Generate and display image color histograms.
---

# Image Histogram Analyzer Skill

## Purpose
Generate and display image color histograms.

## When to Activate
Activate when the user asks to:
- image histogram
- color distribution
- photo analysis

## Core Workflows

```python
from PIL import Image; img.histogram()  # or matplotlib hist of RGB channels
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
