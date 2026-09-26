---
name: writing-review
description: Write balanced reviews for products, books, movies, or restaurants.
---

# Product / Book Review Writer Skill

## Purpose
Write balanced reviews for products, books, movies, or restaurants.

## When to Activate
Activate when the user asks to:
- write review
- review of <product>
- book review

## Core Workflows

Prompt: `Write a balanced {word_count}-word review of {item} covering pros, cons, and a rating out of 10.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
