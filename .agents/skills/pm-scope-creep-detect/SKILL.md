---
name: pm-scope-creep-detect
description: Flag tasks that fall outside the original project scope.
---

# Scope Creep Detector Skill

## Purpose
Flag tasks that fall outside the original project scope.

## When to Activate
Activate when the user asks to:
- scope creep
- out of scope
- scope check
- is this in scope

## Core Workflows

Compare new request against original scope statement, classify as in/out of scope.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
