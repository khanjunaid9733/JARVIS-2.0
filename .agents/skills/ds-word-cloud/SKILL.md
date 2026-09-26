---
name: ds-word-cloud
description: Generate visual word clouds from text documents.
---

# Word Cloud Generator Skill

## Purpose
Generate visual word clouds from text documents.

## When to Activate
Activate when the user asks to:
- word cloud
- word frequency
- text visualization

## Core Workflows

```python
from wordcloud import WordCloud; WordCloud().generate(text).to_file('wc.png')
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
