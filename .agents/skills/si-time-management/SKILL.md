---
name: si-time-management
description: Build a complete time management framework.
---

# Time Management System Skill

## Purpose
Build a complete time management framework.

## When to Activate
Activate when the user asks to:
- time management
- manage time
- time blocking
- prioritization

## Core Workflows

Prompt: `Design a time management system for {context}. Include: prioritization matrix, time blocks, review schedule.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
