---
name: web-api-call
description: Make authenticated HTTP GET/POST/PUT/DELETE calls to any REST API.
---

# Generic API Caller Skill

## Purpose
Make authenticated HTTP GET/POST/PUT/DELETE calls to any REST API.

## When to Activate
Activate when the user asks to:
- call API
- GET <endpoint>
- POST to <url>

## Core Workflows

```python
request = urllib.request.Request(url, data=body, headers=headers, method='POST')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
