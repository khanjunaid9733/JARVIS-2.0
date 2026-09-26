---
name: productivity-flashcard
description: Create and study spaced-repetition flashcard decks.
---

# Flashcard Study System Skill

## Purpose
Create and study spaced-repetition flashcard decks.

## When to Activate
Activate when the user asks to:
- study flashcards
- create flashcard
- quiz me on
- spaced repetition

## Core Workflows

Implement SM-2 spaced repetition algorithm with card state stored in JSON.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
