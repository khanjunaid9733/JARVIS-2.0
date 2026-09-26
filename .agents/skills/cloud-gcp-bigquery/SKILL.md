---
name: cloud-gcp-bigquery
description: Run SQL queries against Google BigQuery and return results.
---

# BigQuery Query Runner Skill

## Purpose
Run SQL queries against Google BigQuery and return results.

## When to Activate
Activate when the user asks to:
- query BigQuery
- run SQL on BigQuery
- BigQuery results

## Core Workflows

```python
from google.cloud import bigquery; bigquery.Client().query(sql).to_dataframe()
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
