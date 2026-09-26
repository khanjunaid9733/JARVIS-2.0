---
name: dev-api-test
description: Test REST API endpoints with custom headers, body, and assertions.
---

# API Endpoint Tester Skill

## Purpose
Test REST API endpoints with custom headers, body, and assertions.

## When to Activate
Activate when the user asks to:
- test API endpoint
- hit <url> with POST
- API smoke test

## Core Workflows

Use urllib.request to make requests and assert expected status codes and response fields.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
