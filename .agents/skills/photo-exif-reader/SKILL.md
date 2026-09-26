---
name: photo-exif-reader
description: Read and display EXIF metadata from image files.
---

# EXIF Metadata Reader Skill

## Purpose
Read and display EXIF metadata from image files.

## When to Activate
Activate when the user asks to:
- EXIF data
- photo metadata
- camera settings
- when was photo taken

## Core Workflows

```python
from PIL import Image; img._getexif()
# or: exifread.process_file(open(path, 'rb'))
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
