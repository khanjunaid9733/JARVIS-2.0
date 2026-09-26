---
name: web-pdf-fetch
description: Download a PDF from URL and extract its text content.
---

# PDF Downloader & Parser Skill

## Purpose
Download a PDF from URL and extract its text content.

## When to Activate
Activate when the user asks to:
- read PDF from <url>
- download and parse PDF

## Core Workflows

Download PDF, use `pdfminer.six` or `pypdf` to extract text pages.

## Best Practices & Safety Invariants
- Always verify preconditions before initiating actions.
- Log all significant actions to the JARVIS event stream.
- Fail-closed with descriptive error messages on any failure.
- Never expose secrets or credentials in event log payloads.
- Respect user-declared privacy and data minimization principles.
