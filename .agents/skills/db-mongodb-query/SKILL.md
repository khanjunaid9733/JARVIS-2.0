---
name: db-mongodb-query
description: Query and insert documents in MongoDB collections.
---

# MongoDB Query Runner Skill

## Purpose
Query and insert documents in MongoDB collections.

## When to Activate
Activate when the user asks to:
- query MongoDB
- find in mongo
- insert document

## Core Workflows

```python
from pymongo import MongoClient; MongoClient(uri)['db']['col'].find({query})
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
