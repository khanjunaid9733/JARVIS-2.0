---
name: pm-project-plan
description: Create a full project plan with milestones, tasks, and timeline.
---

# Project Plan Creator Skill

## Purpose
Create a full project plan with milestones, tasks, and timeline.

## When to Activate
Activate when the user asks to:
- create project plan
- project roadmap
- project schedule
- plan <project>

## Core Workflows

Prompt: `Create a project plan for {project} with phases, milestones, and a {duration} timeline in Gantt chart format.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
