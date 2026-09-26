---
name: desktop-scheduled-tasks
description: Create, list, run, and delete Windows Scheduled Tasks.
---

# Task Scheduler Skill

## Purpose
Create, list, run, and delete Windows Scheduled Tasks.

## When to Activate
Activate when the user asks to:
- schedule a task
- create scheduled job
- list scheduled tasks

## Core Workflows

```powershell
Register-ScheduledTask -Action (New-ScheduledTaskAction -Execute 'python') -Trigger ...
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
