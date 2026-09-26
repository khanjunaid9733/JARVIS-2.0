---
name: files-log-tail
description: Tail, filter, and search log files in real time.
---

# Log File Viewer Skill

## Purpose
Tail, filter, and search log files in real time.

## When to Activate
Activate when the user asks to:
- tail <logfile>
- show last N lines of <log>
- search <log> for <pattern>

## Core Workflows

```python
with open(path) as f: lines = f.readlines()[-100:]
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
