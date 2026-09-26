---
name: assistant-gift-ideas
description: Suggest personalized gift ideas for any occasion and recipient.
---

# Gift Ideas Generator Skill

## Purpose
Suggest personalized gift ideas for any occasion and recipient.

## When to Activate
Activate when the user asks to:
- gift ideas
- what to get
- gift for
- present suggestions

## Core Workflows

Prompt: `Suggest 10 thoughtful gift ideas for a {person} who likes {interests} for {occasion}. Budget: {budget}.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
