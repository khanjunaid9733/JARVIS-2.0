---
name: db-graph-query
description: Query graph databases like Neo4j with Cypher.
---

# Graph Database Query Skill

## Purpose
Query graph databases like Neo4j with Cypher.

## When to Activate
Activate when the user asks to:
- graph query
- Neo4j
- Cypher query
- relationships

## Core Workflows

```python
from neo4j import GraphDatabase; session.run('MATCH (n) RETURN n LIMIT 10')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
