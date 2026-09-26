---
name: dev-env-check
description: Verify all required tools, Python version, and env vars are present.
---

# Environment Checker Skill

## Purpose
Verify all required tools, Python version, and env vars are present.

## When to Activate
Activate when the user asks to:
- check environment
- verify setup
- check dependencies

## Core Workflows

Check each required binary/module with `shutil.which()` and `importlib.util.find_spec()`.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
