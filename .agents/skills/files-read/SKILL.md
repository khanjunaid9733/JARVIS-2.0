---
name: files-read
description: Read any text, JSON, YAML, CSV, or binary file from disk.
---

# Read File Skill

## Purpose
Read any text, JSON, YAML, CSV, or binary file from disk.

## When to Activate
Activate when the user asks to:
- read file
- open file
- show contents of

## Core Workflows

```python
Path(path).read_text(encoding='utf-8')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
