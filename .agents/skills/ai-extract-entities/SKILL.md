---
name: ai-extract-entities
description: Extract named entities (people, places, dates, orgs) from text.
---

# Entity Extractor Skill

## Purpose
Extract named entities (people, places, dates, orgs) from text.

## When to Activate
Activate when the user asks to:
- extract entities
- find names in
- identify people in text

## Core Workflows

Prompt: `Extract all named entities (PERSON, ORG, LOCATION, DATE) from: {text}. Return JSON.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
