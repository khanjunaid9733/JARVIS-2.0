---
name: edu-flashcard-gen
description: Generate spaced-repetition flashcard decks from any content.
---

# Flashcard Generator Skill

## Purpose
Generate spaced-repetition flashcard decks from any content.

## When to Activate
Activate when the user asks to:
- create flashcards
- flashcards for
- study cards

## Core Workflows

Prompt: `Create 20 flashcard pairs (question/answer) about {topic} suitable for memorization.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
