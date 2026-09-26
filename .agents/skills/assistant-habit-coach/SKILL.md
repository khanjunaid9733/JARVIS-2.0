---
name: assistant-habit-coach
description: Guide the creation and maintenance of new positive habits.
---

# Habit Formation Coach Skill

## Purpose
Guide the creation and maintenance of new positive habits.

## When to Activate
Activate when the user asks to:
- form habit
- build routine
- help me habit
- create habit

## Core Workflows

Apply habit loop model: Cue → Routine → Reward. Design habit stack.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
