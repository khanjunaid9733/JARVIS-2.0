---
name: files-json-parse
description: Load, query, modify, and save JSON data files.
---

# JSON Parser Skill

## Purpose
Load, query, modify, and save JSON data files.

## When to Activate
Activate when the user asks to:
- parse JSON
- read JSON
- load JSON from <path>

## Core Workflows

```python
import json; json.loads(Path(path).read_text())
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
