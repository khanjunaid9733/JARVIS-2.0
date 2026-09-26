---
name: browser-multi-tab
description: Open and manage multiple browser tabs simultaneously.
---

# Multi-Tab Manager Skill

## Purpose
Open and manage multiple browser tabs simultaneously.

## When to Activate
Activate when the user asks to:
- open multiple tabs
- new tab
- manage tabs
- parallel browser

## Core Workflows

```python
new_page = context.new_page(); new_page.goto(url2)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
