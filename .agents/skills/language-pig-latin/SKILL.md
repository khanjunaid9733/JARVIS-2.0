---
name: language-pig-latin
description: Convert text to Pig Latin, Leet Speak, or Pig Sty encoding.
---

# Language Games Skill

## Purpose
Convert text to Pig Latin, Leet Speak, or Pig Sty encoding.

## When to Activate
Activate when the user asks to:
- pig latin
- leet speak
- encode
- language games

## Core Workflows

Apply Pig Latin rules: consonant cluster + 'ay', or vowel-start + 'way'.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
