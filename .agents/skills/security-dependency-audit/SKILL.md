---
name: security-dependency-audit
description: Scan project dependencies for known CVEs.
---

# Dependency Vulnerability Audit Skill

## Purpose
Scan project dependencies for known CVEs.

## When to Activate
Activate when the user asks to:
- audit dependencies
- check for CVEs
- vulnerability scan
- npm audit

## Core Workflows

```bash
pip-audit  # Python
npm audit  # Node
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
