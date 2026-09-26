---
name: travel-language-basics
description: Teach essential phrases in any language for a trip.
---

# Travel Language Basics Skill

## Purpose
Teach essential phrases in any language for a trip.

## When to Activate
Activate when the user asks to:
- basic <language>
- survival phrases
- common phrases in
- hello in

## Core Workflows

Prompt: `Teach me 20 essential {language} phrases for a traveler: greetings, directions, food, emergencies. Include pronunciation.`

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
