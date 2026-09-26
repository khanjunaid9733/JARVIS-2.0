---
name: assistant-task-automate
description: Automate repetitive personal tasks with a single command.
---

# Task Automator Skill

## Purpose
Automate repetitive personal tasks with a single command.

## When to Activate
Activate when the user asks to:
- automate this
- I always do
- create automation for
- recurring task

## Core Workflows

Analyze repetitive task pattern → route to n8n workflow or OS scheduler.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
