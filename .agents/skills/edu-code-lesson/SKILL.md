---
name: edu-code-lesson
description: Create coding tutorials with exercises for any language or framework.
---

# Coding Lesson Generator Skill

## Purpose
Create coding tutorials with exercises for any language or framework.

## When to Activate
Activate when the user asks to:
- coding lesson
- teach Python
- programming tutorial
- code exercises

## Core Workflows

Prompt: `Create a {duration} tutorial on {topic} in {language} with explanations and 3 practice exercises.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
