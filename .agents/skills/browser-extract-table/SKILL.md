---
name: browser-extract-table
description: Extract all data from HTML tables on a web page.
---

# Table Data Extractor Skill

## Purpose
Extract all data from HTML tables on a web page.

## When to Activate
Activate when the user asks to:
- extract table
- scrape table
- table data from page

## Core Workflows

Use `page.query_selector_all('table')` then iterate rows and cells.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
