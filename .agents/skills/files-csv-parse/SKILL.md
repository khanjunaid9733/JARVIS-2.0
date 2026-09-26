---
name: files-csv-parse
description: Read, filter, transform, and write CSV spreadsheet files.
---

# CSV Parser & Writer Skill

## Purpose
Read, filter, transform, and write CSV spreadsheet files.

## When to Activate
Activate when the user asks to:
- parse CSV
- read spreadsheet
- open CSV file

## Core Workflows

```python
import csv; list(csv.DictReader(open(path)))
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
