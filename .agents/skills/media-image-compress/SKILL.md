---
name: media-image-compress
description: Compress images to reduce file size without quality loss.
---

# Image Compressor Skill

## Purpose
Compress images to reduce file size without quality loss.

## When to Activate
Activate when the user asks to:
- compress image
- reduce image size
- optimize image

## Core Workflows

```python
Image.open(path).save(out, optimize=True, quality=85)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
