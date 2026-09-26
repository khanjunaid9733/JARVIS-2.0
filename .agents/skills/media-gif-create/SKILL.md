---
name: media-gif-create
description: Create animated GIFs from a sequence of images or video clip.
---

# GIF Creator Skill

## Purpose
Create animated GIFs from a sequence of images or video clip.

## When to Activate
Activate when the user asks to:
- create GIF
- make animated GIF
- gif from video

## Core Workflows

```python
from PIL import Image; Image.save(out_gif, save_all=True, append_images=[...])
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
