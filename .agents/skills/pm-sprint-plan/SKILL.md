---
name: pm-sprint-plan
description: Plan an Agile sprint with story points and velocity.
---

# Agile Sprint Planner Skill

## Purpose
Plan an Agile sprint with story points and velocity.

## When to Activate
Activate when the user asks to:
- sprint planning
- agile sprint
- user stories
- story points

## Core Workflows

Prompt: `Create a {duration}-week sprint plan from backlog: {stories}. Estimate story points and assign priority.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
