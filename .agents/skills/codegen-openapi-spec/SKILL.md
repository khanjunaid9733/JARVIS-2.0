---
name: codegen-openapi-spec
description: Generate OpenAPI/Swagger specification from API description.
---

# OpenAPI Spec Generator Skill

## Purpose
Generate OpenAPI/Swagger specification from API description.

## When to Activate
Activate when the user asks to:
- OpenAPI spec
- Swagger doc
- API specification
- generate API docs

## Core Workflows

Generate complete OpenAPI 3.0 YAML with paths, schemas, responses, and authentication.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
