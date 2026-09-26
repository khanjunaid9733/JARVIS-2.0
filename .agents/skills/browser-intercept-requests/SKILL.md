---
name: browser-intercept-requests
description: Intercept and modify browser network requests for testing.
---

# Network Request Interceptor Skill

## Purpose
Intercept and modify browser network requests for testing.

## When to Activate
Activate when the user asks to:
- intercept requests
- mock API response
- network interception

## Core Workflows

```python
page.route('**/*.json', lambda route: route.fulfill(body=mock_json))
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
