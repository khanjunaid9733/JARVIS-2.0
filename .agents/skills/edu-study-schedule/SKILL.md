---
name: edu-study-schedule
description: Build an optimized study schedule for exams or courses.
---

# Study Schedule Builder Skill

## Purpose
Build an optimized study schedule for exams or courses.

## When to Activate
Activate when the user asks to:
- study schedule
- exam prep
- study plan
- revision timetable

## Core Workflows

Distribute topics across available days, prioritize weak areas, include review sessions.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
