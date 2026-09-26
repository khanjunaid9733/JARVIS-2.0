---
name: pm-task-breakdown
description: Break down a project into a Work Breakdown Structure.
---

# Task Breakdown (WBS) Skill

## Purpose
Break down a project into a Work Breakdown Structure.

## When to Activate
Activate when the user asks to:
- break down project
- WBS
- task decomposition
- subtasks for

## Core Workflows

Prompt: `Create a Work Breakdown Structure for {project}. List all deliverables, tasks, and subtasks hierarchically.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
