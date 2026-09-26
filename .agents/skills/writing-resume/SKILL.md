---
name: writing-resume
description: Create or enhance a professional resume from a skill list.
---

# Resume Builder Skill

## Purpose
Create or enhance a professional resume from a skill list.

## When to Activate
Activate when the user asks to:
- write resume
- update resume
- create CV
- resume builder

## Core Workflows

Prompt: `Create a {format} resume for a {role} with experience: {experience}, skills: {skills}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
