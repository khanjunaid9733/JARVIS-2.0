---
name: browser-cookie-manager
description: Export, import, and manage browser cookies for sessions.
---

# Browser Cookie Manager Skill

## Purpose
Export, import, and manage browser cookies for sessions.

## When to Activate
Activate when the user asks to:
- export cookies
- save session
- load cookies
- browser cookies

## Core Workflows

```python
cookies = context.cookies(); context.add_cookies(cookies)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
