---
name: browser-auto-scroll
description: Automatically scroll web pages to load infinite scroll content.
---

# Auto Scroller Skill

## Purpose
Automatically scroll web pages to load infinite scroll content.

## When to Activate
Activate when the user asks to:
- scroll page
- load all content
- infinite scroll
- scroll to bottom

## Core Workflows

```python
page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
