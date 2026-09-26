---
name: edu-grammar-lesson
description: Create grammar lessons and exercises for any language.
---

# Grammar Lesson Generator Skill

## Purpose
Create grammar lessons and exercises for any language.

## When to Activate
Activate when the user asks to:
- grammar lesson
- teach me grammar
- language exercises

## Core Workflows

Prompt: `Create a grammar lesson on {topic} in {language} with examples, rules, and practice exercises.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
