---
name: pm-dependency-map
description: Map task dependencies and identify the critical path.
---

# Task Dependency Mapper Skill

## Purpose
Map task dependencies and identify the critical path.

## When to Activate
Activate when the user asks to:
- critical path
- task dependencies
- project network
- dependency diagram

## Core Workflows

Build a DAG from task dependencies, compute longest path = critical path.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
