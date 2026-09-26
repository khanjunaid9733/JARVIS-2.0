---
name: browser-navigate
description: Open URLs and navigate to pages headlessly with Playwright.
---

# Browser Navigator Skill

## Purpose
Open URLs and navigate to pages headlessly with Playwright.

## When to Activate
Activate when the user asks to:
- open website
- navigate to
- go to <url>
- browse to

## Core Workflows

```python
from playwright.sync_api import sync_playwright; page.goto(url)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
