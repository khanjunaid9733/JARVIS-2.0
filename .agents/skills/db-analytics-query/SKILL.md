---
name: db-analytics-query
description: Run fast analytical queries with DuckDB on CSV/Parquet files.
---

# Analytics Query (DuckDB) Skill

## Purpose
Run fast analytical queries with DuckDB on CSV/Parquet files.

## When to Activate
Activate when the user asks to:
- analytics query
- analyze data file
- DuckDB query

## Core Workflows

```python
import duckdb; duckdb.sql('SELECT * FROM read_csv_auto(path)').df()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
