---
name: photo-thumbnail
description: Generate standardized thumbnails for websites or apps.
---

# Thumbnail Generator Skill

## Purpose
Generate standardized thumbnails for websites or apps.

## When to Activate
Activate when the user asks to:
- thumbnail
- resize to thumbnail
- profile picture resize

## Core Workflows

```python
Image.open(path).thumbnail((200,200), Image.LANCZOS).save(out)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
