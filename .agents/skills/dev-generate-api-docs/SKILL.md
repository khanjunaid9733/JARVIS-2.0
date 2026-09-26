---
name: dev-generate-api-docs
description: Generate API docs from docstrings using Sphinx or pdoc.
---

# API Documentation Generator Skill

## Purpose
Generate API docs from docstrings using Sphinx or pdoc.

## When to Activate
Activate when the user asks to:
- generate docs
- create API docs
- build documentation

## Core Workflows

```bash
pdoc --html --output-dir docs/ src/jarvis
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
