---
name: pm-trello-card
description: Add cards to Trello boards and lists via API.
---

# Trello Card Creator Skill

## Purpose
Add cards to Trello boards and lists via API.

## When to Activate
Activate when the user asks to:
- add Trello card
- create Trello task
- Trello board

## Core Workflows

POST to Trello API `/1/cards` with idList, name, and description.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
