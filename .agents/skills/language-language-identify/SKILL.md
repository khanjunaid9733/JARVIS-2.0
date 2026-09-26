---
name: language-language-identify
description: Identify the language of any text.
---

# Language Identifier Skill

## Purpose
Identify the language of any text.

## When to Activate
Activate when the user asks to:
- what language is this
- identify language
- detect language
- is this Spanish

## Core Workflows

```python
from langdetect import detect; detect(text)  # returns ISO 639-1
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
