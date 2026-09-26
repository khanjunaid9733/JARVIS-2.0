---
name: files-yaml-parse
description: Load and write YAML configuration files.
---

# YAML Parser Skill

## Purpose
Load and write YAML configuration files.

## When to Activate
Activate when the user asks to:
- parse YAML
- read YAML config
- load yaml from <path>

## Core Workflows

```python
import yaml; yaml.safe_load(open(path))
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
