---
name: files-diff
description: Compare two files or directories and show differences.
---

# File Diff / Comparison Skill

## Purpose
Compare two files or directories and show differences.

## When to Activate
Activate when the user asks to:
- diff <file1> <file2>
- compare files
- what changed in

## Core Workflows

```python
import difflib; difflib.unified_diff(a.splitlines(), b.splitlines())
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
