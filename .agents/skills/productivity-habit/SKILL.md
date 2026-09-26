---
name: productivity-habit
description: Track daily habits and streaks.
---

# Habit Tracker Skill

## Purpose
Track daily habits and streaks.

## When to Activate
Activate when the user asks to:
- log habit
- habit streak
- did I do <habit>
- habit tracker

## Core Workflows

Store daily check-ins in JARVIS_HOME/habits.json, compute streaks.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
