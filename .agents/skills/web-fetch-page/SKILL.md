---
name: web-fetch-page
description: Download and extract clean text from any public URL.
---

# Fetch Web Page Skill

## Purpose
Download and extract clean text from any public URL.

## When to Activate
Activate when the user asks to:
- open URL
- read page
- fetch website

## Core Workflows

```python
urllib.request.urlopen(url) -> HTML -> HTMLParser -> clean text
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
