---
name: edu-quiz-generate
description: Create multiple-choice quizzes on any topic.
---

# Quiz Generator Skill

## Purpose
Create multiple-choice quizzes on any topic.

## When to Activate
Activate when the user asks to:
- quiz me on
- create quiz
- test my knowledge
- practice questions

## Core Workflows

Prompt: `Create a 10-question multiple choice quiz on {topic} with 4 options each and an answer key.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
