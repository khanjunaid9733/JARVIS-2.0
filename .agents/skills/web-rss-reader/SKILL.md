---
name: web-rss-reader
description: Fetch and parse RSS/Atom feeds for latest articles.
---

# RSS Feed Reader Skill

## Purpose
Fetch and parse RSS/Atom feeds for latest articles.

## When to Activate
Activate when the user asks to:
- latest news from <site>
- read RSS feed
- follow <blog>

## Core Workflows

```python
import xml.etree.ElementTree as ET; ET.fromstring(urlopen(rss_url).read())
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
