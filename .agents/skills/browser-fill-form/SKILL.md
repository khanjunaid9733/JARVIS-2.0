---
name: browser-fill-form
description: Fill in web form fields with provided values.
---

# Form Filler Skill

## Purpose
Fill in web form fields with provided values.

## When to Activate
Activate when the user asks to:
- fill form
- enter data
- type in field
- fill <field> with

## Core Workflows

```python
page.fill('#email', email); page.fill('#password', password)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
