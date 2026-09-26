---
name: health-workout-plan
description: Create personalized workout plans by goal, fitness level, and equipment.
---

# Workout Plan Generator Skill

## Purpose
Create personalized workout plans by goal, fitness level, and equipment.

## When to Activate
Activate when the user asks to:
- workout plan
- exercise routine
- fitness program
- gym plan

## Core Workflows

Prompt: `Create a {days}-day workout plan for {goal} at {level} fitness level with {equipment}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
