---
name: browser-screenshot-web
description: Capture full-page screenshots of any URL.
---

# Website Screenshot Skill

## Purpose
Capture full-page screenshots of any URL.

## When to Activate
Activate when the user asks to:
- screenshot <url>
- capture web page
- website screenshot

## Core Workflows

```python
page.screenshot(path='screenshot.png', full_page=True)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
