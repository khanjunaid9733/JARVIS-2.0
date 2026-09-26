---
name: language-word-game
description: Help with Wordle, crosswords, Scrabble, and word puzzles.
---

# Word Game Helper Skill

## Purpose
Help with Wordle, crosswords, Scrabble, and word puzzles.

## When to Activate
Activate when the user asks to:
- Wordle help
- crossword clue
- Scrabble words
- word puzzle

## Core Workflows

Filter Datamuse API words by pattern, length, and letter constraints.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
