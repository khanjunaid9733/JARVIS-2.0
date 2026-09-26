---
name: codegen-crud-app
description: Generate a full CRUD web application with a database backend.
---

# CRUD App Generator Skill

## Purpose
Generate a full CRUD web application with a database backend.

## When to Activate
Activate when the user asks to:
- CRUD app
- full stack app
- create web app with database

## Core Workflows

Generate: models, migrations, REST endpoints, and a basic HTML frontend.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
