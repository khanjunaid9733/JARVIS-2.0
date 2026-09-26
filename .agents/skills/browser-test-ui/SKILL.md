---
name: browser-test-ui
description: Run automated UI tests and check element states.
---

# UI Test Runner Skill

## Purpose
Run automated UI tests and check element states.

## When to Activate
Activate when the user asks to:
- test UI
- UI automation test
- check element
- assert page state

## Core Workflows

```python
expect(page.locator('h1')).to_have_text('Dashboard')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
