---
name: browser-pdf-from-url
description: Convert any web page to a PDF document.
---

# Web Page to PDF Skill

## Purpose
Convert any web page to a PDF document.

## When to Activate
Activate when the user asks to:
- save page as PDF
- convert to PDF
- print page to PDF

## Core Workflows

```python
page.pdf(path='output.pdf', format='A4', print_background=True)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
