---
name: edu-debate-practice
description: Argue both sides of any topic to practice critical thinking.
---

# Debate Practice Partner Skill

## Purpose
Argue both sides of any topic to practice critical thinking.

## When to Activate
Activate when the user asks to:
- debate
- argue against
- devil's advocate
- counterargument

## Core Workflows

Prompt: `Present the strongest {side} argument for: {topic}. Include 5 specific points with evidence.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
