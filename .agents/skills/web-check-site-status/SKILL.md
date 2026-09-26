---
name: web-check-site-status
description: Check if a website is up, its HTTP status code, and response time.
---

# Website Status Checker Skill

## Purpose
Check if a website is up, its HTTP status code, and response time.

## When to Activate
Activate when the user asks to:
- is <site> down
- check website status
- ping <url>

## Core Workflows

```python
import urllib.request, time; t=time.time(); urllib.request.urlopen(url, timeout=5)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
