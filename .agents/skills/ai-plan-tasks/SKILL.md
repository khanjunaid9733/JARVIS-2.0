---
name: ai-plan-tasks
description: Break down any goal into actionable tasks and subtasks.
---

# AI Task Planner Skill

## Purpose
Break down any goal into actionable tasks and subtasks.

## When to Activate
Activate when the user asks to:
- plan how to
- break down goal
- create task list for
- steps to

## Core Workflows

Prompt: `Create a detailed step-by-step plan to achieve: {goal}. Number each step.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
