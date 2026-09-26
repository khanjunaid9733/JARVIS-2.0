---
name: photo-ocr
description: Extract text from images and screenshots using OCR.
---

# Image Text Extractor (OCR) Skill

## Purpose
Extract text from images and screenshots using OCR.

## When to Activate
Activate when the user asks to:
- OCR
- read text from image
- text in screenshot
- extract text from photo

## Core Workflows

```python
import pytesseract; pytesseract.image_to_string(Image.open(path))
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
