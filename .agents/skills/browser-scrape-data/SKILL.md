---
name: browser-scrape-data
description: Extract structured data from web pages using selectors.
---

# Web Data Scraper Skill

## Purpose
Extract structured data from web pages using selectors.

## When to Activate
Activate when the user asks to:
- scrape <site>
- extract data from
- web scraper
- crawl page

## Core Workflows

```python
page.query_selector_all('table tr td')  # or use BeautifulSoup
```

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
