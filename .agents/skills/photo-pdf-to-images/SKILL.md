---
name: photo-pdf-to-images
description: Convert PDF pages to image files.
---

# PDF Page to Images Skill

## Purpose
Convert PDF pages to image files.

## When to Activate
Activate when the user asks to:
- PDF to images
- convert PDF pages
- extract images from PDF

## Core Workflows

```python
from pdf2image import convert_from_path; pages = convert_from_path(pdf_path)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
