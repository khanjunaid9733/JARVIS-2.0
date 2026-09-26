---
name: db-export-csv
description: Export query results to a CSV file.
---

# Database to CSV Exporter Skill

## Purpose
Export query results to a CSV file.

## When to Activate
Activate when the user asks to:
- export to CSV
- save query results
- database to spreadsheet

## Core Workflows

```python
import csv; writer = csv.DictWriter(f, fieldnames); writer.writerows(results)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
