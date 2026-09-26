---
name: codegen-rest-api
description: Generate a complete REST API using FastAPI or Flask.
---

# REST API Generator Skill

## Purpose
Generate a complete REST API using FastAPI or Flask.

## When to Activate
Activate when the user asks to:
- create REST API
- build API
- FastAPI
- Flask API

## Core Workflows

Generate: routes, models (Pydantic), CRUD operations, error handlers, and OpenAPI docs.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
