---
name: files-excel-parse
description: Read and write Excel `.xlsx` workbooks and sheets.
---

# Excel Spreadsheet Parser Skill

## Purpose
Read and write Excel `.xlsx` workbooks and sheets.

## When to Activate
Activate when the user asks to:
- open Excel file
- read spreadsheet
- parse XLSX

## Core Workflows

```python
import openpyxl; wb = openpyxl.load_workbook(path)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
