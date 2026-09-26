---
name: language-rhyme-finder
description: Find rhyming words for any word.
---

# Rhyme Finder Skill

## Purpose
Find rhyming words for any word.

## When to Activate
Activate when the user asks to:
- rhymes with
- words that rhyme
- rhyming dictionary

## Core Workflows

GET Datamuse API `/words?rel_rhy={word}` for rhyming words list.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
