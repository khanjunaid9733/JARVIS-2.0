---
name: dev-dependency-install
description: Install Python packages, npm modules, or system dependencies.
---

# Install Dependencies Skill

## Purpose
Install Python packages, npm modules, or system dependencies.

## When to Activate
Activate when the user asks to:
- install <package>
- pip install
- npm install

## Core Workflows

```bash
uv pip install <package>  # Python
npm install <package>   # Node
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
