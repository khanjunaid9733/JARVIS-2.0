---
name: dev-create-project
description: Scaffold a new Python, Node, or web project with best-practice structure.
---

# New Project Scaffolder Skill

## Purpose
Scaffold a new Python, Node, or web project with best-practice structure.

## When to Activate
Activate when the user asks to:
- create new project
- scaffold <language> project
- init new repo

## Core Workflows

Use cookiecutter templates or custom generators.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
