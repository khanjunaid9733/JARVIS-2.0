---
name: science-graph-theory
description: Analyze graph structures: shortest path, cycles, spanning trees.
---

# Graph Theory Analyzer Skill

## Purpose
Analyze graph structures: shortest path, cycles, spanning trees.

## When to Activate
Activate when the user asks to:
- shortest path
- graph analysis
- Dijkstra
- spanning tree

## Core Workflows

```python
import networkx as nx; nx.shortest_path(G, source, target)
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
