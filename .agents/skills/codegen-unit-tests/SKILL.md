---
name: codegen-unit-tests
description: Generate pytest unit tests for any Python function or module.
---

# Unit Test Generator Skill

## Purpose
Generate pytest unit tests for any Python function or module.

## When to Activate
Activate when the user asks to:
- generate tests
- write unit tests
- test coverage
- pytest for

## Core Workflows

Analyze function signatures and behavior, generate test cases including edge cases.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
