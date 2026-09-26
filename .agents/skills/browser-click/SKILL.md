---
name: browser-click
description: Click buttons, links, and elements on web pages.
---

# Element Clicker Skill

## Purpose
Click buttons, links, and elements on web pages.

## When to Activate
Activate when the user asks to:
- click <button>
- click <element>
- submit form
- click button

## Core Workflows

```python
page.click('button[type=submit]')  # or by text: page.get_by_text('Login').click()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
