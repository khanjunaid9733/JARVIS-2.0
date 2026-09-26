---
name: language-synonym
description: Find synonyms and antonyms for any word.
---

# Synonym & Antonym Finder Skill

## Purpose
Find synonyms and antonyms for any word.

## When to Activate
Activate when the user asks to:
- synonym for
- antonym
- another word for
- opposite of

## Core Workflows

GET Datamuse API `/words?ml={word}` or Merriam-Webster Thesaurus API.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
